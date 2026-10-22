"""
Injects realistic attack and benign flows directly to the backend for testing/demo.
Feature values match CICIDS2017 dataset distributions.
"""
import requests
import time
import random

BACKEND = "http://localhost:8081/api/traffic/analyze"
DELAY   = 1.5   # secunde între fiecare flux trimis


def send(flow):
    try:
        r = requests.post(BACKEND, json=flow, timeout=5)
        result = r.json()
        status = "ANOMALY ⚠  " + result.get("label", "") if result.get("anomaly") else "normal"
        score = result.get("anomalyScore", 0)
        print(f"  {flow['sourceIp']}:{flow['destinationPort']:5d} [{flow['protocol']}]"
              f"  score={score:.3f}  {status}")
    except Exception as e:
        print(f"  ERROR: {e}")
    time.sleep(DELAY)


# ─── TRAFIC NORMAL ────────────────────────────────────────────────────────────

def benign_web(n=5):
    """Navigare web normală — HTTP/HTTPS."""
    print(f"\n[BENIGN] Web browsing x{n}")
    for _ in range(n):
        dur = random.uniform(0.5, 4.0)
        fwd = random.randint(4, 12)
        bwd = random.randint(8, 30)
        fwd_b = fwd * random.randint(200, 600)
        bwd_b = bwd * random.randint(400, 1400)
        total = fwd_b + bwd_b
        pkts = fwd + bwd
        send({
            "sourceIp": f"192.168.1.{random.randint(10, 50)}",
            "destinationIp": f"93.184.{random.randint(1,254)}.{random.randint(1,254)}",
            "sourcePort": random.randint(49152, 65535),
            "destinationPort": random.choice([80, 443, 443, 443]),
            "protocol": "TCP",
            "totalFwdPackets": fwd,
            "totalBwdPackets": bwd,
            "totalFwdBytes": fwd_b,
            "totalBwdBytes": bwd_b,
            "flowDuration": round(dur, 6),
            "flowBytesPerSec": round(total / dur, 2),
            "flowPacketsPerSec": round(pkts / dur, 2),
            "synFlagCount": 1,
            "rstFlagCount": 0,
            "avgPacketSize": round(total / pkts, 2),
            "finFlagCount": 1,
            "ackFlagCount": pkts - 1,
            "pshFlagCount": bwd,
            "urgFlagCount": 0,
            "fwdPacketLenMin": 54,
            "fwdPacketLenMax": random.randint(600, 1400),
            "bwdPacketLenMax": random.randint(800, 1460),
            "packetLenStd": round(random.uniform(200, 500), 2),
        })


def benign_dns(n=4):
    """Interogări DNS normale — UDP port 53."""
    print(f"\n[BENIGN] DNS queries x{n}")
    for _ in range(n):
        dur = random.uniform(0.01, 0.1)
        send({
            "sourceIp": f"192.168.1.{random.randint(10, 50)}",
            "destinationIp": "8.8.8.8",
            "sourcePort": random.randint(49152, 65535),
            "destinationPort": 53,
            "protocol": "UDP",
            "totalFwdPackets": 1,
            "totalBwdPackets": 1,
            "totalFwdBytes": random.randint(60, 90),
            "totalBwdBytes": random.randint(80, 200),
            "flowDuration": round(dur, 6),
            "flowBytesPerSec": round(random.randint(140, 290) / dur, 2),
            "flowPacketsPerSec": round(2 / dur, 2),
            "synFlagCount": 0,
            "rstFlagCount": 0,
            "avgPacketSize": round(random.uniform(70, 145), 2),
            "finFlagCount": 0,
            "ackFlagCount": 0,
            "pshFlagCount": 0,
            "urgFlagCount": 0,
            "fwdPacketLenMin": 60,
            "fwdPacketLenMax": 90,
            "bwdPacketLenMax": 200,
            "packetLenStd": round(random.uniform(20, 60), 2),
        })


# ─── ATACURI CUNOSCUTE ────────────────────────────────────────────────────────

def port_scan(n=20):
    """Port scan — CICIDS2017 CRITICAL: dur=20-60s(µs), fwd_b=0, bwd_b=12, avg_pkt=3, score>0.83."""
    print(f"\n[ATTACK] PortScan x{n} from 10.0.0.99")
    targets = [3306, 1433, 3690, 5900, 8080, 6379, 27017, 5432, 9200, 2181,
               4444, 6666, 8443, 9090, 10000, 7001, 7002, 8888, 9999, 11211]
    random.shuffle(targets)
    for port in targets[:n]:
        dur = random.randint(20_000_000, 60_000_000)  # 20-60 secunde în microsecunde
        fwd_b = 0
        bwd_b = 12
        dur_s = dur / 1_000_000
        send({
            "sourceIp": "10.0.0.99",
            "destinationIp": "192.168.1.1",
            "sourcePort": random.randint(40000, 65000),
            "destinationPort": port,
            "protocol": "TCP",
            "totalFwdPackets": 2,
            "totalBwdPackets": 2,
            "totalFwdBytes": fwd_b,
            "totalBwdBytes": bwd_b,
            "flowDuration": float(dur),
            "flowBytesPerSec": round(bwd_b / dur_s, 4),
            "flowPacketsPerSec": round(4 / dur_s, 4),
            "synFlagCount": 0,
            "rstFlagCount": 0,
            "avgPacketSize": 3.0,
            "finFlagCount": 0,
            "ackFlagCount": 0,
            "pshFlagCount": 1,
            "urgFlagCount": 0,
            "fwdPacketLenMin": 0,
            "fwdPacketLenMax": 0,
            "bwdPacketLenMax": 6,
            "packetLenStd": 3.286,
        })


def dos_hulk(n=3):
    print(f"\n[ATTACK] DoS Hulk x{n} from 10.0.0.99")
    for _ in range(n):
        dur = random.uniform(0.5, 3.0)
        fwd_pkts = random.randint(800, 3000)
        bwd_pkts = random.randint(200, 800)
        fwd_bytes = fwd_pkts * random.randint(400, 700)
        bwd_bytes = bwd_pkts * random.randint(200, 500)
        total_bytes = fwd_bytes + bwd_bytes
        total_pkts = fwd_pkts + bwd_pkts
        send({
            "sourceIp": "10.0.0.99",
            "destinationIp": "192.168.1.1",
            "sourcePort": random.randint(1024, 65000),
            "destinationPort": 80,
            "protocol": "TCP",
            "totalFwdPackets": fwd_pkts,
            "totalBwdPackets": bwd_pkts,
            "totalFwdBytes": fwd_bytes,
            "totalBwdBytes": bwd_bytes,
            "flowDuration": round(dur, 4),
            "flowBytesPerSec": round(total_bytes / dur, 2),
            "flowPacketsPerSec": round(total_pkts / dur, 2),
            "synFlagCount": 1,
            "rstFlagCount": 0,
            "avgPacketSize": round(total_bytes / total_pkts, 2),
            "finFlagCount": 0,
            "ackFlagCount": fwd_pkts + bwd_pkts - 1,
            "pshFlagCount": fwd_pkts,
            "urgFlagCount": 0,
            "fwdPacketLenMin": 292,
            "fwdPacketLenMax": 765,
            "bwdPacketLenMax": 512,
            "packetLenStd": round(random.uniform(100, 200), 2),
        })


def ddos(n=3):
    print(f"\n[ATTACK] DDoS x{n} from 10.0.0.99")
    for _ in range(n):
        dur = random.uniform(0.1, 1.0)
        pkts = random.randint(3000, 8000)
        byt = pkts * 64
        send({
            "sourceIp": "10.0.0.99",
            "destinationIp": "192.168.1.1",
            "sourcePort": random.randint(1024, 65000),
            "destinationPort": 80,
            "protocol": "UDP",
            "totalFwdPackets": pkts,
            "totalBwdPackets": 0,
            "totalFwdBytes": byt,
            "totalBwdBytes": 0,
            "flowDuration": round(dur, 4),
            "flowBytesPerSec": round(byt / dur, 2),
            "flowPacketsPerSec": round(pkts / dur, 2),
            "synFlagCount": 0,
            "rstFlagCount": 0,
            "avgPacketSize": 64.0,
            "finFlagCount": 0,
            "ackFlagCount": 0,
            "pshFlagCount": 0,
            "urgFlagCount": 0,
            "fwdPacketLenMin": 64,
            "fwdPacketLenMax": 64,
            "bwdPacketLenMax": 0,
            "packetLenStd": 0.0,
        })


def ssh_patator(n=5):
    """SSH-Patator brute force — CICIDS2017 CRITICAL: fwd=14, bwd=15, fwd_b=1304, bwd_b=2153, score=0.83."""
    print(f"\n[ATTACK] SSH-Patator brute force x{n} from 10.0.0.99")
    for _ in range(n):
        dur = random.randint(3_500_000, 6_000_000)  # 3.5-6 secunde în microsecunde
        fwd_b = 1304
        bwd_b = 2153
        total = fwd_b + bwd_b
        pkts = 14 + 15
        dur_s = dur / 1_000_000
        send({
            "sourceIp": "10.0.0.99",
            "destinationIp": "192.168.1.1",
            "sourcePort": random.randint(1024, 65000),
            "destinationPort": 22,
            "protocol": "TCP",
            "totalFwdPackets": 14,
            "totalBwdPackets": 15,
            "totalFwdBytes": fwd_b,
            "totalBwdBytes": bwd_b,
            "flowDuration": float(dur),
            "flowBytesPerSec": round(total / dur_s, 2),
            "flowPacketsPerSec": round(pkts / dur_s, 4),
            "synFlagCount": 0,
            "rstFlagCount": 0,
            "avgPacketSize": round(total / pkts, 3),
            "finFlagCount": 0,
            "ackFlagCount": 0,
            "pshFlagCount": 1,
            "urgFlagCount": 0,
            "fwdPacketLenMin": 0,
            "fwdPacketLenMax": 640,
            "bwdPacketLenMax": 976,
            "packetLenStd": 250.082,
        })


def ftp_patator(n=4):
    """FTP-Patator brute force — CICIDS2017 CRITICAL: dur=200-250µs, fwd_b=14-16, avg_pkt=9.333, score>0.84."""
    print(f"\n[ATTACK] FTP-Patator brute force x{n} from 10.0.0.99")
    for _ in range(n):
        dur = random.randint(200, 250)  # 200-250 microsecunde
        fwd_b = random.randint(14, 16)
        dur_s = dur / 1_000_000
        send({
            "sourceIp": "10.0.0.99",
            "destinationIp": "192.168.1.1",
            "sourcePort": random.randint(1024, 65000),
            "destinationPort": 21,
            "protocol": "TCP",
            "totalFwdPackets": 2,
            "totalBwdPackets": 1,
            "totalFwdBytes": fwd_b,
            "totalBwdBytes": 0,
            "flowDuration": float(dur),
            "flowBytesPerSec": round(fwd_b / dur_s, 2),
            "flowPacketsPerSec": round(3 / dur_s, 2),
            "synFlagCount": 1,
            "rstFlagCount": 0,
            "avgPacketSize": 9.333,
            "finFlagCount": 0,
            "ackFlagCount": 1,
            "pshFlagCount": 0,
            "urgFlagCount": 0,
            "fwdPacketLenMin": 0,
            "fwdPacketLenMax": fwd_b,
            "bwdPacketLenMax": 0,
            "packetLenStd": 8.083,
        })


def dos_slowloris(n=3):
    """DoS Slowloris — CICIDS2017 CRITICAL: fwd=15,bwd=3,fwd_b=2541,bwd_b=6,fwd_max=231,std=116, score=0.90."""
    print(f"\n[ATTACK] DoS Slowloris x{n} from 10.0.0.99")
    for _ in range(n):
        dur = random.randint(95_000_000, 115_000_000)  # 95-115 secunde în microsecunde
        fwd_b = random.randint(2480, 2560)
        bwd_b = 6
        total = fwd_b + bwd_b
        pkts = 18
        dur_s = dur / 1_000_000
        send({
            "sourceIp": "10.0.0.99",
            "destinationIp": "192.168.1.1",
            "sourcePort": random.randint(1024, 65000),
            "destinationPort": 80,
            "protocol": "TCP",
            "totalFwdPackets": 15,
            "totalBwdPackets": 3,
            "totalFwdBytes": fwd_b,
            "totalBwdBytes": bwd_b,
            "flowDuration": float(dur),
            "flowBytesPerSec": round(total / dur_s, 4),
            "flowPacketsPerSec": round(pkts / dur_s, 4),
            "synFlagCount": 0,
            "rstFlagCount": 0,
            "avgPacketSize": round(total / pkts, 3),
            "finFlagCount": 0,
            "ackFlagCount": 0,
            "pshFlagCount": 1,
            "urgFlagCount": 0,
            "fwdPacketLenMin": 0,
            "fwdPacketLenMax": 231,
            "bwdPacketLenMax": 6,
            "packetLenStd": round(random.uniform(116.0, 118.0), 3),
        })


def web_attack(n=4):
    """Web Attack (XSS / Brute Force) — scurt, puține pachete, bytes aproape zero.
    CICIDS2017 median: dur=5.5s, 3 fwd+1 bwd pachete, ~0 bytes, psh=1."""
    print(f"\n[ATTACK] Web Attack (XSS/BruteForce) x{n} from 10.0.0.99")
    for _ in range(n):
        dur = random.uniform(4.0, 7.0)
        fwd = random.randint(2, 4)
        bwd = random.randint(1, 2)
        fwd_b = fwd * random.randint(1, 4)   # aproape 0 — caracteristic XSS/BF
        bwd_b = bwd * random.randint(1, 4)
        total = fwd_b + bwd_b
        pkts = fwd + bwd
        send({
            "sourceIp": "10.0.0.99",
            "destinationIp": "192.168.1.1",
            "sourcePort": random.randint(1024, 65000),
            "destinationPort": 80,
            "protocol": "TCP",
            "totalFwdPackets": fwd,
            "totalBwdPackets": bwd,
            "totalFwdBytes": fwd_b,
            "totalBwdBytes": bwd_b,
            "flowDuration": round(dur, 4),
            "flowBytesPerSec": round(total / dur, 4),
            "flowPacketsPerSec": round(pkts / dur, 4),
            "synFlagCount": 1,
            "rstFlagCount": 0,
            "avgPacketSize": round(total / pkts, 4) if pkts > 0 else 0.0,
            "finFlagCount": 1,
            "ackFlagCount": pkts - 1,
            "pshFlagCount": 1,
            "urgFlagCount": 0,
            "fwdPacketLenMin": 1,
            "fwdPacketLenMax": 8,
            "bwdPacketLenMax": 8,
            "packetLenStd": round(random.uniform(2.0, 5.5), 2),
        })




# ─── ANOMALII NECUNOSCUTE (detectate de Isolation Forest ca UNKNOWN) ─────────

def slow_exfiltration(n=3):
    """Exfiltrare lentă de date — volum mare, rată mică, asimetric fwd>>bwd.
    Nu seamănă cu niciun atac CICIDS2017 dar iese din normalul IF."""
    print(f"\n[UNKNOWN] Slow data exfiltration x{n} from 10.0.0.55")
    for _ in range(n):
        dur = random.uniform(120.0, 400.0)
        fwd = random.randint(800, 2000)
        bwd = random.randint(5, 15)            # aproape zero bwd — asimetric
        fwd_b = fwd * random.randint(1300, 1460)  # pachete mari, aproape MTU
        bwd_b = bwd * random.randint(40, 60)
        total = fwd_b + bwd_b
        pkts = fwd + bwd
        send({
            "sourceIp": "10.0.0.55",
            "destinationIp": "185.199.108.10",
            "sourcePort": random.randint(49152, 65535),
            "destinationPort": 443,
            "protocol": "TCP",
            "totalFwdPackets": fwd,
            "totalBwdPackets": bwd,
            "totalFwdBytes": fwd_b,
            "totalBwdBytes": bwd_b,
            "flowDuration": round(dur, 4),
            "flowBytesPerSec": round(total / dur, 2),
            "flowPacketsPerSec": round(pkts / dur, 2),
            "synFlagCount": 1,
            "rstFlagCount": 0,
            "avgPacketSize": round(total / pkts, 2),
            "finFlagCount": 1,
            "ackFlagCount": pkts - 1,
            "pshFlagCount": fwd,
            "urgFlagCount": 0,
            "fwdPacketLenMin": 1300,
            "fwdPacketLenMax": 1460,
            "bwdPacketLenMax": 60,
            "packetLenStd": round(random.uniform(2, 15), 2),  # extrem de uniform
        })


def dns_tunneling(n=4):
    """DNS Tunneling — sute de interogări DNS cu pachete de 10x mai mari decât normal.
    Normal DNS: 1-2 pachete, 60-90 bytes. Tunnel: 80-120 pachete, 400-500 bytes."""
    print(f"\n[UNKNOWN] DNS Tunneling x{n} from 10.0.0.55")
    for _ in range(n):
        dur = random.uniform(1.0, 3.0)
        fwd = random.randint(80, 120)
        bwd = random.randint(60, 100)
        fwd_b = fwd * random.randint(400, 500)
        bwd_b = bwd * random.randint(420, 510)
        total = fwd_b + bwd_b
        pkts = fwd + bwd
        send({
            "sourceIp": "10.0.0.55",
            "destinationIp": "8.8.8.8",
            "sourcePort": random.randint(49152, 65535),
            "destinationPort": 53,
            "protocol": "UDP",
            "totalFwdPackets": fwd,
            "totalBwdPackets": bwd,
            "totalFwdBytes": fwd_b,
            "totalBwdBytes": bwd_b,
            "flowDuration": round(dur, 4),
            "flowBytesPerSec": round(total / dur, 2),
            "flowPacketsPerSec": round(pkts / dur, 2),
            "synFlagCount": 0,
            "rstFlagCount": 0,
            "avgPacketSize": round(total / pkts, 2),
            "finFlagCount": 0,
            "ackFlagCount": 0,
            "pshFlagCount": 0,
            "urgFlagCount": 0,
            "fwdPacketLenMin": 380,
            "fwdPacketLenMax": 512,
            "bwdPacketLenMax": 512,
            "packetLenStd": round(random.uniform(30, 60), 2),
        })


def covert_beacon(n=3):
    """Beacon C2 — conexiune de 1 oră cu 48 pachete identice de 64 bytes.
    flowBytesPerSec < 1, packetLenStd=0 — structurally impossible in normal traffic."""
    print(f"\n[UNKNOWN] Covert C2 beacon x{n} from 10.0.0.55")
    for _ in range(n):
        dur = random.uniform(3000.0, 3600.0)  # ~1 oră
        fwd = random.randint(22, 26)
        bwd = random.randint(22, 26)
        pkt_size = 64
        fwd_b = fwd * pkt_size
        bwd_b = bwd * pkt_size
        total = fwd_b + bwd_b
        pkts = fwd + bwd
        send({
            "sourceIp": "10.0.0.55",
            "destinationIp": "91.108.4.200",
            "sourcePort": random.randint(49152, 65535),
            "destinationPort": random.choice([443, 8443, 4443]),
            "protocol": "TCP",
            "totalFwdPackets": fwd,
            "totalBwdPackets": bwd,
            "totalFwdBytes": fwd_b,
            "totalBwdBytes": bwd_b,
            "flowDuration": round(dur, 4),
            "flowBytesPerSec": round(total / dur, 4),  # ~0.8 bytes/sec
            "flowPacketsPerSec": round(pkts / dur, 6),  # ~0.013 pkt/sec
            "synFlagCount": 1,
            "rstFlagCount": 0,
            "avgPacketSize": float(pkt_size),
            "finFlagCount": 0,
            "ackFlagCount": pkts - 1,
            "pshFlagCount": fwd // 2,
            "urgFlagCount": 0,
            "fwdPacketLenMin": pkt_size,
            "fwdPacketLenMax": pkt_size,
            "bwdPacketLenMax": pkt_size,
            "packetLenStd": 0.0,  # perfect uniform
        })


def icmp_exfiltration(n=2):
    """Exfiltrare prin ICMP — volume mari, neobișnuit pentru ping normal."""
    print(f"\n[UNKNOWN] ICMP exfiltration x{n} from 10.0.0.55")
    for _ in range(n):
        dur = random.uniform(2.0, 10.0)
        pkts = random.randint(200, 600)
        pkt_size = random.randint(900, 1400)  # ICMP mare — normal e 64-128 bytes
        total_b = pkts * pkt_size
        send({
            "sourceIp": "10.0.0.55",
            "destinationIp": "185.199.108.10",
            "sourcePort": 0,
            "destinationPort": 0,
            "protocol": "ICMP",
            "totalFwdPackets": pkts,
            "totalBwdPackets": 0,
            "totalFwdBytes": total_b,
            "totalBwdBytes": 0,
            "flowDuration": round(dur, 4),
            "flowBytesPerSec": round(total_b / dur, 2),
            "flowPacketsPerSec": round(pkts / dur, 2),
            "synFlagCount": 0,
            "rstFlagCount": 0,
            "avgPacketSize": float(pkt_size),
            "finFlagCount": 0,
            "ackFlagCount": 0,
            "pshFlagCount": 0,
            "urgFlagCount": 0,
            "fwdPacketLenMin": pkt_size - 10,
            "fwdPacketLenMax": pkt_size,
            "bwdPacketLenMax": 0,
            "packetLenStd": round(random.uniform(1, 8), 2),
        })


# ─── SECVENȚA DEMO ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  IDS DEMO — Injectare fluxuri de rețea")
    print("=" * 60)

    print("\n>>> FAZA 1: Trafic normal")
    benign_web(5)
    benign_dns(4)
    time.sleep(5)

    print("\n>>> FAZA 2: Atacuri cunoscute (detectate de Random Forest)")
    port_scan(20)
    time.sleep(8)
    dos_slowloris(3)
    time.sleep(5)
    ssh_patator(4)
    time.sleep(5)
    ftp_patator(3)
    time.sleep(5)
    dos_hulk(3)

    print("\n>>> FAZA 3: Anomalii necunoscute (detectate de Isolation Forest ca UNKNOWN)")
    time.sleep(8)
    slow_exfiltration(3)
    time.sleep(5)
    dns_tunneling(4)
    time.sleep(5)
    icmp_exfiltration(2)

    print("\n>>> FAZA 4: Trafic normal după atac")
    time.sleep(8)
    benign_web(3)
    benign_dns(2)

    print("\n" + "=" * 60)
    print("  Done. Verifică frontend-ul pentru alerte.")
    print("=" * 60)
