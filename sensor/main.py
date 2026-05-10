"""
Real-time network sensor.
Captures packets with Scapy, aggregates them into flows, then sends each
completed flow to the backend for ML-based anomaly analysis.

Run with administrator / root privileges so Scapy can open raw sockets.
Usage:
    python main.py [--iface <interface>] [--interval <seconds>] [--backend <url>] [--session <id>]
"""

import argparse
import time
import threading
import requests
from collections import defaultdict
from datetime import datetime

try:
    from scapy.all import sniff, IP, TCP, UDP, ICMP
    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False
    print("[WARN] Scapy not installed. Running in simulation mode.")

BACKEND_URL = "http://localhost:8080"
FLOW_INTERVAL = 5  # seconds per aggregation window


class FlowAggregator:
    """Aggregates raw packets into per-(src,dst,dport,proto) flow records."""

    def __init__(self):
        self.lock = threading.Lock()
        self.flows = defaultdict(lambda: {
            "packet_count": 0,
            "byte_count": 0,
            "start_time": time.time(),
            "connections": 0,
        })

    def add_packet(self, src_ip, dst_ip, src_port, dst_port, protocol, size):
        key = (src_ip, dst_ip, src_port, dst_port, protocol)
        with self.lock:
            f = self.flows[key]
            f["packet_count"] += 1
            f["byte_count"] += size
            f["connections"] += 1

    def flush(self) -> list:
        """Return all flows accumulated so far and reset."""
        with self.lock:
            snapshot = dict(self.flows)
            self.flows.clear()
        now = time.time()
        result = []
        for (src_ip, dst_ip, src_port, dst_port, proto), f in snapshot.items():
            duration = max(now - f["start_time"], 0.001)
            cps = f["connections"] / duration
            result.append({
                "sourceIp": src_ip,
                "destinationIp": dst_ip,
                "sourcePort": src_port,
                "destinationPort": dst_port,
                "protocol": proto,
                "packetCount": f["packet_count"],
                "byteCount": f["byte_count"],
                "duration": round(duration, 4),
                "connectionsPerSecond": round(cps, 4),
            })
        return result


aggregator = FlowAggregator()


def packet_callback(pkt):
    if not pkt.haslayer(IP):
        return
    ip = pkt[IP]
    src_ip = ip.src
    dst_ip = ip.dst
    size = len(pkt)

    if pkt.haslayer(TCP):
        proto = "TCP"
        src_port = pkt[TCP].sport
        dst_port = pkt[TCP].dport
    elif pkt.haslayer(UDP):
        proto = "UDP"
        src_port = pkt[UDP].sport
        dst_port = pkt[UDP].dport
    elif pkt.haslayer(ICMP):
        proto = "ICMP"
        src_port = 0
        dst_port = 0
    else:
        return

    aggregator.add_packet(src_ip, dst_ip, src_port, dst_port, proto, size)


def send_flows(backend_url: str, session_id=None):
    flows = aggregator.flush()
    if not flows:
        return
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Sending {len(flows)} flows to backend...")
    for flow in flows:
        if session_id:
            flow["sessionId"] = session_id
        try:
            resp = requests.post(f"{backend_url}/api/traffic/analyze", json=flow, timeout=5)
            result = resp.json()
            status = "ANOMALY" if result.get("anomaly") else "normal"
            score = result.get("anomalyScore", 0)
            print(f"  {flow['sourceIp']} -> {flow['destinationIp']}:{flow['destinationPort']}"
                  f" [{flow['protocol']}] => {status} (score={score:.3f})")
        except requests.RequestException as e:
            print(f"  [ERROR] Failed to send flow: {e}")


def flush_loop(backend_url: str, interval: int, session_id=None, stop_event: threading.Event = None):
    while not (stop_event and stop_event.is_set()):
        time.sleep(interval)
        send_flows(backend_url, session_id)


def simulate_traffic(aggregator: FlowAggregator, stop_event: threading.Event):
    """Generate synthetic traffic when Scapy is unavailable."""
    import random
    normal_ips = ["192.168.1.10", "192.168.1.20", "192.168.1.30"]
    attack_ip = "10.0.0.99"

    while not stop_event.is_set():
        # Normal traffic
        src = random.choice(normal_ips)
        aggregator.add_packet(src, "192.168.1.1", random.randint(1024, 65535),
                               random.choice([80, 443, 53]), "TCP", random.randint(200, 5000))

        # Occasional anomalous burst (port scan simulation)
        if random.random() < 0.05:
            for port in range(20, 70):
                aggregator.add_packet(attack_ip, "192.168.1.1", random.randint(1024, 65535),
                                       port, "TCP", 64)
        time.sleep(0.1)


def main():
    parser = argparse.ArgumentParser(description="IDS Network Sensor")
    parser.add_argument("--iface", default=None, help="Network interface to sniff")
    parser.add_argument("--interval", type=int, default=FLOW_INTERVAL, help="Flow flush interval (seconds)")
    parser.add_argument("--backend", default=BACKEND_URL, help="Backend URL")
    parser.add_argument("--session", type=int, default=None, help="Monitoring session ID")
    args = parser.parse_args()

    stop_event = threading.Event()

    flush_thread = threading.Thread(
        target=flush_loop,
        args=(args.backend, args.interval, args.session, stop_event),
        daemon=True
    )
    flush_thread.start()

    if SCAPY_AVAILABLE:
        print(f"Starting packet capture on interface: {args.iface or 'default'}")
        print(f"Sending flows to: {args.backend} every {args.interval}s")
        try:
            sniff(iface=args.iface, prn=packet_callback, store=False)
        except KeyboardInterrupt:
            print("\nStopping sensor...")
    else:
        print("Scapy not available — running simulation mode.")
        print(f"Sending simulated flows to: {args.backend} every {args.interval}s")
        sim_thread = threading.Thread(target=simulate_traffic, args=(aggregator, stop_event), daemon=True)
        sim_thread.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping simulation...")

    stop_event.set()


if __name__ == "__main__":
    main()
