"""
Real-time network sensor.

Captures packets with Scapy, aggregates them into per-(src,dst,sport,dport,proto)
flows, then sends each completed flow to the backend for ML analysis.

The 12 features sent match exactly the CICIDS2017 feature set used to train the model:
  destination_port, protocol, flow_duration, total_fwd_packets, total_bwd_packets,
  total_fwd_bytes, total_bwd_bytes, flow_bytes_per_sec, flow_packets_per_sec,
  syn_flag_count, rst_flag_count, avg_packet_size

Run with administrator / root privileges for real capture.
Usage:
    python main.py [--iface <iface>] [--interval <sec>] [--backend <url>] [--session <id>]
    python main.py                        # simulation mode (no admin needed)
"""

import argparse
import time
import threading
import requests
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime

try:
    from scapy.all import sniff, IP, TCP, UDP, ICMP
    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False
    print("[WARN] Scapy not installed. Running in simulation mode.")

BACKEND_URL = "http://localhost:8080"
FLOW_INTERVAL = 5   # seconds per aggregation window

# Protocol number → string (for display) and number (for model)
PROTO_NUM = {"TCP": 6, "UDP": 17, "ICMP": 1}


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
    rst_count: int = 0
    packet_sizes: list = field(default_factory=list)


class FlowAggregator:
    """Bidirectional per-5-tuple flow aggregation with TCP flag tracking."""

    def __init__(self):
        self.lock = threading.Lock()
        self.flows: dict[tuple, FlowRecord] = {}

    def _canonical_key(self, src_ip, dst_ip, src_port, dst_port, proto):
        """Normalise so (A→B) and (B→A) use the same record."""
        if (src_ip, src_port) < (dst_ip, dst_port):
            return (src_ip, dst_ip, src_port, dst_port, proto)
        return (dst_ip, src_ip, dst_port, src_port, proto)

    def add_packet(self, src_ip, dst_ip, src_port, dst_port, proto, size,
                   syn=False, rst=False, is_forward=True):
        key = self._canonical_key(src_ip, dst_ip, src_port, dst_port, proto)
        with self.lock:
            if key not in self.flows:
                # Store canonical src/dst as key[0]/key[1]
                self.flows[key] = FlowRecord(
                    src_ip=key[0], dst_ip=key[1],
                    src_port=key[2], dst_port=key[3],
                    protocol=proto,
                )
            rec = self.flows[key]
            if is_forward:
                rec.fwd_packets += 1
                rec.fwd_bytes += size
            else:
                rec.bwd_packets += 1
                rec.bwd_bytes += size
            if syn:
                rec.syn_count += 1
            if rst:
                rec.rst_count += 1
            rec.packet_sizes.append(size)

    def flush(self) -> list[dict]:
        with self.lock:
            snapshot = dict(self.flows)
            self.flows.clear()
        now = time.time()
        result = []
        for rec in snapshot.values():
            duration = max(now - rec.start_time, 0.001)
            total_pkts = rec.fwd_packets + rec.bwd_packets
            total_bytes = rec.fwd_bytes + rec.bwd_bytes
            avg_size = (sum(rec.packet_sizes) / len(rec.packet_sizes)
                        if rec.packet_sizes else 0.0)
            result.append({
                "sourceIp":          rec.src_ip,
                "destinationIp":     rec.dst_ip,
                "sourcePort":        rec.src_port,
                "destinationPort":   rec.dst_port,
                "protocol":          rec.protocol,
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
            })
        return result


aggregator = FlowAggregator()


# ---------------------------------------------------------------------------
# Scapy packet callback
# ---------------------------------------------------------------------------

def packet_callback(pkt):
    if not pkt.haslayer(IP):
        return
    ip = pkt[IP]
    size = len(pkt)
    src_ip, dst_ip = ip.src, ip.dst

    if pkt.haslayer(TCP):
        tcp = pkt[TCP]
        flags = tcp.flags
        aggregator.add_packet(
            src_ip, dst_ip, tcp.sport, tcp.dport, "TCP", size,
            syn=bool(flags & 0x02),
            rst=bool(flags & 0x04),
            is_forward=True,   # directional tracking is simplified here
        )
    elif pkt.haslayer(UDP):
        udp = pkt[UDP]
        aggregator.add_packet(src_ip, dst_ip, udp.sport, udp.dport, "UDP", size)
    elif pkt.haslayer(ICMP):
        aggregator.add_packet(src_ip, dst_ip, 0, 0, "ICMP", size)


# ---------------------------------------------------------------------------
# Flush loop
# ---------------------------------------------------------------------------

def send_flows(backend_url: str, session_id=None):
    flows = aggregator.flush()
    if not flows:
        return
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] Sending {len(flows)} flow(s) to backend...")
    for flow in flows:
        if session_id:
            flow["sessionId"] = session_id
        try:
            resp = requests.post(f"{backend_url}/api/traffic/analyze",
                                 json=flow, timeout=5)
            result = resp.json()
            status = "ANOMALY ⚠" if result.get("anomaly") else "normal"
            score = result.get("anomalyScore", 0)
            print(f"  {flow['sourceIp']}:{flow['sourcePort']} → "
                  f"{flow['destinationIp']}:{flow['destinationPort']}"
                  f" [{flow['protocol']}]  pkts={flow['totalFwdPackets']+flow['totalBwdPackets']}"
                  f"  {status} (score={score:.3f})")
        except requests.RequestException as e:
            print(f"  [ERROR] {e}")


def flush_loop(backend_url: str, interval: int, session_id, stop: threading.Event):
    while not stop.is_set():
        time.sleep(interval)
        send_flows(backend_url, session_id)


# ---------------------------------------------------------------------------
# Simulation mode
# ---------------------------------------------------------------------------

def simulate_traffic(stop: threading.Event):
    import random
    normal_ips = ["192.168.1.10", "192.168.1.20", "192.168.1.30"]
    attacker_ip = "10.0.0.99"

    while not stop.is_set():
        # --- Normal web/DNS traffic ---
        src = random.choice(normal_ips)
        proto = random.choice(["TCP", "TCP", "TCP", "UDP"])
        dport = random.choice([80, 443, 53, 8080])
        size = random.randint(200, 8000)
        sport = random.randint(1024, 65535)
        aggregator.add_packet(src, "192.168.1.1", sport, dport, proto, size,
                               syn=(proto == "TCP" and random.random() < 0.1))

        # --- Simulate bwd packets ---
        bwd_size = random.randint(200, 4000)
        aggregator.add_packet("192.168.1.1", src, dport, sport, proto, bwd_size,
                               is_forward=False)

        # --- Occasional port scan burst (5% chance) ---
        if random.random() < 0.05:
            print("[SIM] Injecting port scan burst from 10.0.0.99")
            for port in range(20, 80):
                aggregator.add_packet(attacker_ip, "192.168.1.1",
                                       random.randint(40000, 65535), port,
                                       "TCP", 64, syn=True, rst=random.random() < 0.3)

        # --- Occasional DoS burst (2% chance) ---
        if random.random() < 0.02:
            print("[SIM] Injecting DoS burst from 10.0.0.99")
            for _ in range(200):
                aggregator.add_packet(attacker_ip, "192.168.1.1",
                                       random.randint(1024, 65535), 80,
                                       "TCP", random.randint(60, 120), syn=True)

        time.sleep(0.05)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="IDS Network Sensor")
    parser.add_argument("--iface", default=None)
    parser.add_argument("--interval", type=int, default=FLOW_INTERVAL)
    parser.add_argument("--backend", default=BACKEND_URL)
    parser.add_argument("--session", type=int, default=None)
    args = parser.parse_args()

    stop_event = threading.Event()
    flush_thread = threading.Thread(
        target=flush_loop,
        args=(args.backend, args.interval, args.session, stop_event),
        daemon=True,
    )
    flush_thread.start()

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
        sim_thread = threading.Thread(target=simulate_traffic, args=(stop_event,), daemon=True)
        sim_thread.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping simulation...")

    stop_event.set()


if __name__ == "__main__":
    main()
