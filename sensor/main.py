"""
Real-time network sensor.

Captures packets with Scapy, aggregates them into per-(src,dst,sport,dport,proto)
flows, then sends each completed flow to the backend for ML analysis.

The 19 features sent match the expanded CICIDS2017 feature set:
  Base (11): destination_port, protocol, flow_duration, total_fwd/bwd_packets,
             total_fwd/bwd_bytes, flow_bytes/packets_per_sec, syn/rst_flag_count, avg_packet_size
  Extended (8): fin/ack/psh/urg_flag_count, fwd_packet_len_min/max, bwd_packet_len_max, packet_len_std

Run with administrator / root privileges for real capture.
Usage:
    python main.py [--iface <iface>] [--interval <sec>] [--backend <url>] [--session <id>]
    python main.py                        # simulation mode (no admin needed)
"""

import argparse
import math
import random
import time
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime

import requests

try:
    from scapy.all import sniff, IP, TCP, UDP, ICMP
    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False
    print("[WARN] Scapy not installed. Running in simulation mode.")

BACKEND_URL   = "http://localhost:8081"
FLOW_INTERVAL = 5

RAPID_SYN_THRESHOLD   = 50
RAPID_FLOOD_BYTES     = 2_000_000


@dataclass
class FlowRecord:
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    protocol: str

    start_time: float = field(default_factory=time.time)
    fwd_packets: int = 0
    bwd_packets: int = 0
    fwd_bytes: int = 0
    bwd_bytes: int = 0
    syn_count: int = 0
    fin_count: int = 0
    rst_count: int = 0
    ack_count: int = 0
    psh_count: int = 0
    urg_count: int = 0
    fwd_packet_sizes: list = field(default_factory=list)
    bwd_packet_sizes: list = field(default_factory=list)


class FlowAggregator:
    """Bidirectional per-5-tuple flow aggregation with TCP flag tracking."""

    def __init__(self):
        self.lock = threading.Lock()
        self.flows: dict[tuple, FlowRecord] = {}

    def _canonical_key(self, src_ip, dst_ip, src_port, dst_port, proto):
        if (src_ip, src_port) < (dst_ip, dst_port):
            return (src_ip, dst_ip, src_port, dst_port, proto)
        return (dst_ip, src_ip, dst_port, src_port, proto)

    def add_packet(self, src_ip, dst_ip, src_port, dst_port, proto, size,
                   syn=False, fin=False, rst=False, ack=False, psh=False, urg=False,
                   is_forward=True):
        key = self._canonical_key(src_ip, dst_ip, src_port, dst_port, proto)
        with self.lock:
            if key not in self.flows:
                self.flows[key] = FlowRecord(
                    src_ip=key[0], dst_ip=key[1],
                    src_port=key[2], dst_port=key[3],
                    protocol=proto,
                )
            rec = self.flows[key]
            if is_forward:
                rec.fwd_packets += 1
                rec.fwd_bytes += size
                rec.fwd_packet_sizes.append(size)
            else:
                rec.bwd_packets += 1
                rec.bwd_bytes += size
                rec.bwd_packet_sizes.append(size)
            if syn: rec.syn_count += 1
            if fin: rec.fin_count += 1
            if rst: rec.rst_count += 1
            if ack: rec.ack_count += 1
            if psh: rec.psh_count += 1
            if urg: rec.urg_count += 1

    def flush(self) -> list[dict]:
        with self.lock:
            snapshot = dict(self.flows)
            self.flows.clear()
        now = time.time()
        result = []
        for rec in snapshot.values():
            duration = max(now - rec.start_time, 0.001)
            total_pkts  = rec.fwd_packets + rec.bwd_packets
            total_bytes = rec.fwd_bytes + rec.bwd_bytes
            all_sizes   = rec.fwd_packet_sizes + rec.bwd_packet_sizes

            avg_size = (sum(all_sizes) / len(all_sizes)) if all_sizes else 0.0

            fwd_min = min(rec.fwd_packet_sizes) if rec.fwd_packet_sizes else 0
            fwd_max = max(rec.fwd_packet_sizes) if rec.fwd_packet_sizes else 0
            bwd_max = max(rec.bwd_packet_sizes) if rec.bwd_packet_sizes else 0

            if len(all_sizes) > 1:
                mean_s = sum(all_sizes) / len(all_sizes)
                variance = sum((x - mean_s) ** 2 for x in all_sizes) / len(all_sizes)
                pkt_std = math.sqrt(variance)
            else:
                pkt_std = 0.0

            result.append({
                "sourceIp":          rec.src_ip,
                "destinationIp":     rec.dst_ip,
                "sourcePort":        rec.src_port,
                "destinationPort":   rec.dst_port,
                "protocol":          rec.protocol,
                # Base flow metrics
                "totalFwdPackets":   rec.fwd_packets,
                "totalBwdPackets":   rec.bwd_packets,
                "totalFwdBytes":     rec.fwd_bytes,
                "totalBwdBytes":     rec.bwd_bytes,
                "flowDuration":      round(duration, 6),
                "flowBytesPerSec":   round(total_bytes / duration, 4),
                "flowPacketsPerSec": round(total_pkts / duration, 4),
                "synFlagCount":      rec.syn_count,
                "rstFlagCount":      rec.rst_count,
                "avgPacketSize":     round(avg_size, 4),
                # Extended metrics
                "finFlagCount":      rec.fin_count,
                "ackFlagCount":      rec.ack_count,
                "pshFlagCount":      rec.psh_count,
                "urgFlagCount":      rec.urg_count,
                "fwdPacketLenMin":   fwd_min,
                "fwdPacketLenMax":   fwd_max,
                "bwdPacketLenMax":   bwd_max,
                "packetLenStd":      round(pkt_std, 4),
            })
        return result


aggregator = FlowAggregator()
_backend_ok = True


# Scapy packet callback

def packet_callback(pkt):
    if not pkt.haslayer(IP):
        return
    ip   = pkt[IP]
    size = len(pkt)

    if pkt.haslayer(TCP):
        tcp   = pkt[TCP]
        flags = int(tcp.flags)
        aggregator.add_packet(
            ip.src, ip.dst, tcp.sport, tcp.dport, "TCP", size,
            syn=bool(flags & 0x02),
            fin=bool(flags & 0x01),
            rst=bool(flags & 0x04),
            ack=bool(flags & 0x10),
            psh=bool(flags & 0x08),
            urg=bool(flags & 0x20),
            is_forward=True,
        )
    elif pkt.haslayer(UDP):
        udp = pkt[UDP]
        aggregator.add_packet(ip.src, ip.dst, udp.sport, udp.dport, "UDP", size)
    elif pkt.haslayer(ICMP):
        aggregator.add_packet(ip.src, ip.dst, 0, 0, "ICMP", size)


# Send flows with retry + reconnect logic

def send_flows(backend_url: str, session_id=None) -> int:
    global _backend_ok
    flows = aggregator.flush()
    if not flows:
        return 0

    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] Sending {len(flows)} flow(s) to backend...")
    sent = 0

    for flow in flows:
        if session_id:
            flow["sessionId"] = session_id

        for attempt in range(3):
            try:
                resp = requests.post(
                    f"{backend_url}/api/traffic/analyze", json=flow, timeout=5
                )
                result = resp.json()
                if not _backend_ok:
                    print("[INFO] Backend reconnected.")
                    _backend_ok = True
                status = "ANOMALY ⚠" if result.get("anomaly") else "normal"
                score  = result.get("anomalyScore", 0)
                label  = result.get("label", "")
                print(f"  {flow['sourceIp']}:{flow['sourcePort']} → "
                      f"{flow['destinationIp']}:{flow['destinationPort']}"
                      f" [{flow['protocol']}]"
                      f"  pkts={flow['totalFwdPackets'] + flow['totalBwdPackets']}"
                      f"  {status} {label} (score={score:.3f})")
                sent += 1
                break
            except requests.RequestException as e:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                else:
                    if _backend_ok:
                        print(f"[WARN] Backend unreachable: {e}")
                        _backend_ok = False

    return sent


# Flush loop (regular interval + exponential backoff when backend is down)

def flush_loop(backend_url: str, interval: int, session_id, stop: threading.Event):
    extra_wait = 0
    while not stop.is_set():
        time.sleep(interval + extra_wait)
        sent = send_flows(backend_url, session_id)
        if sent == 0 and not _backend_ok:
            extra_wait = min(extra_wait + 5, 30)
            print(f"[WARN] Backend down. Next retry in {interval + extra_wait}s")
        else:
            extra_wait = 0


# Rapid-detection loop — flushes early on obvious attack patterns

def rapid_detect_loop(backend_url: str, session_id, stop: threading.Event):
    while not stop.is_set():
        time.sleep(1.0)
        with aggregator.lock:
            suspicious = any(
                r.syn_count >= RAPID_SYN_THRESHOLD
                or (r.fwd_bytes + r.bwd_bytes) >= RAPID_FLOOD_BYTES
                for r in aggregator.flows.values()
            )
        if suspicious:
            print("[RAPID] Suspicious flow pattern detected — flushing early")
            send_flows(backend_url, session_id)


# Simulation mode

def simulate_traffic(stop: threading.Event):
    normal_ips  = ["192.168.1.10", "192.168.1.20", "192.168.1.30"]
    attacker_ip = "10.0.0.99"

    while not stop.is_set():
        src   = random.choice(normal_ips)
        proto = random.choice(["TCP", "TCP", "TCP", "UDP"])
        dport = random.choice([80, 443, 53, 8080])
        sport = random.randint(1024, 65535)
        size  = random.randint(200, 8000)
        is_syn = proto == "TCP" and random.random() < 0.1
        is_ack = proto == "TCP" and random.random() < 0.7
        is_psh = proto == "TCP" and random.random() < 0.3
        aggregator.add_packet(
            src, "192.168.1.1", sport, dport, proto, size,
            syn=is_syn, ack=is_ack, psh=is_psh,
        )
        bwd_size = random.randint(200, 4000)
        aggregator.add_packet(
            "192.168.1.1", src, dport, sport, proto, bwd_size,
            ack=True, is_forward=False,
        )

        if random.random() < 0.05:
            print("[SIM] Injecting port scan burst from 10.0.0.99")
            for port in range(20, 80):
                aggregator.add_packet(
                    attacker_ip, "192.168.1.1",
                    random.randint(40000, 65535), port, "TCP", 64,
                    syn=True, rst=random.random() < 0.3,
                )

        if random.random() < 0.02:
            print("[SIM] Injecting DoS burst from 10.0.0.99")
            for _ in range(300):
                aggregator.add_packet(
                    attacker_ip, "192.168.1.1",
                    random.randint(1024, 65535), 80, "TCP",
                    random.randint(60, 120),
                    syn=True, ack=random.random() < 0.5,
                )

        time.sleep(0.05)



def main():
    parser = argparse.ArgumentParser(description="IDS Network Sensor")
    parser.add_argument("--iface",    default=None)
    parser.add_argument("--interval", type=int, default=FLOW_INTERVAL)
    parser.add_argument("--backend",  default=BACKEND_URL)
    parser.add_argument("--session",  type=int, default=None)
    args = parser.parse_args()

    stop_event = threading.Event()

    flush_thread = threading.Thread(
        target=flush_loop,
        args=(args.backend, args.interval, args.session, stop_event),
        daemon=True,
    )
    rapid_thread = threading.Thread(
        target=rapid_detect_loop,
        args=(args.backend, args.session, stop_event),
        daemon=True,
    )
    flush_thread.start()
    rapid_thread.start()

    if SCAPY_AVAILABLE:
        print(f"Starting real packet capture | iface={args.iface or 'default'}"
              f" | backend={args.backend} | interval={args.interval}s")
        try:
            sniff(iface=args.iface, prn=packet_callback, store=False)
        except KeyboardInterrupt:
            print("\nStopping sensor...")
    else:
        print(f"Simulation mode | backend={args.backend} | interval={args.interval}s")
        print("Press Ctrl+C to stop.")
        sim_thread = threading.Thread(
            target=simulate_traffic, args=(stop_event,), daemon=True
        )
        sim_thread.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping simulation...")

    stop_event.set()


if __name__ == "__main__":
    main()
