"""
Teste unitare pentru FlowAggregator din senzorul de rețea.
Rulare: python -m pytest test_sensor.py -v
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(__file__))
from main import FlowAggregator, RAPID_SYN_THRESHOLD, RAPID_FLOOD_BYTES


# --------------------------------------------------------------------------- #
# 1. Cheia canonică                                                            #
# --------------------------------------------------------------------------- #
class TestCanonicalKey:

    def test_cheia_este_simetrica(self):
        agg = FlowAggregator()
        k1 = agg._canonical_key("10.0.0.1", "10.0.0.2", 1000, 80, "TCP")
        k2 = agg._canonical_key("10.0.0.2", "10.0.0.1", 80, 1000, "TCP")
        assert k1 == k2

    def test_fluxuri_diferite_chei_diferite(self):
        agg = FlowAggregator()
        k1 = agg._canonical_key("10.0.0.1", "10.0.0.2", 1000, 80, "TCP")
        k2 = agg._canonical_key("10.0.0.1", "10.0.0.3", 1000, 80, "TCP")
        assert k1 != k2

    def test_protocolul_face_parte_din_cheie(self):
        agg = FlowAggregator()
        k1 = agg._canonical_key("10.0.0.1", "10.0.0.2", 1000, 80, "TCP")
        k2 = agg._canonical_key("10.0.0.1", "10.0.0.2", 1000, 80, "UDP")
        assert k1 != k2

    def test_port_diferit_cheie_diferita(self):
        agg = FlowAggregator()
        k1 = agg._canonical_key("10.0.0.1", "10.0.0.2", 1000, 80, "TCP")
        k2 = agg._canonical_key("10.0.0.1", "10.0.0.2", 1000, 443, "TCP")
        assert k1 != k2


# --------------------------------------------------------------------------- #
# 2. Adăugarea pachetelor                                                      #
# --------------------------------------------------------------------------- #
class TestAddPacket:

    def test_pachet_forward_contorizat_corect(self):
        agg = FlowAggregator()
        agg.add_packet("1.1.1.1", "2.2.2.2", 1000, 80, "TCP", 500, is_forward=True)
        key = agg._canonical_key("1.1.1.1", "2.2.2.2", 1000, 80, "TCP")
        rec = agg.flows[key]
        assert rec.fwd_packets == 1
        assert rec.fwd_bytes == 500
        assert rec.bwd_packets == 0

    def test_pachet_backward_contorizat_corect(self):
        agg = FlowAggregator()
        agg.add_packet("1.1.1.1", "2.2.2.2", 1000, 80, "TCP", 200, is_forward=False)
        key = agg._canonical_key("1.1.1.1", "2.2.2.2", 1000, 80, "TCP")
        rec = agg.flows[key]
        assert rec.bwd_packets == 1
        assert rec.bwd_bytes == 200
        assert rec.fwd_packets == 0

    def test_pachete_bidirecționale_acelasi_flux(self):
        agg = FlowAggregator()
        agg.add_packet("1.1.1.1", "2.2.2.2", 1000, 80, "TCP", 500, is_forward=True)
        agg.add_packet("2.2.2.2", "1.1.1.1", 80, 1000, "TCP", 300, is_forward=False)
        assert len(agg.flows) == 1

    def test_flag_syn_contorizat(self):
        agg = FlowAggregator()
        agg.add_packet("1.1.1.1", "2.2.2.2", 1000, 80, "TCP", 64, syn=True)
        key = agg._canonical_key("1.1.1.1", "2.2.2.2", 1000, 80, "TCP")
        assert agg.flows[key].syn_count == 1

    def test_flag_rst_contorizat(self):
        agg = FlowAggregator()
        agg.add_packet("1.1.1.1", "2.2.2.2", 1000, 80, "TCP", 64, rst=True)
        key = agg._canonical_key("1.1.1.1", "2.2.2.2", 1000, 80, "TCP")
        assert agg.flows[key].rst_count == 1

    def test_flag_uri_multiple_contorizate(self):
        agg = FlowAggregator()
        agg.add_packet("1.1.1.1", "2.2.2.2", 1000, 80, "TCP", 64,
                       syn=True, ack=True, psh=True)
        key = agg._canonical_key("1.1.1.1", "2.2.2.2", 1000, 80, "TCP")
        rec = agg.flows[key]
        assert rec.syn_count == 1
        assert rec.ack_count == 1
        assert rec.psh_count == 1
        assert rec.fin_count == 0

    def test_fluxuri_diferite_inregistrate_separat(self):
        agg = FlowAggregator()
        agg.add_packet("1.1.1.1", "2.2.2.2", 1000, 80, "TCP", 500)
        agg.add_packet("3.3.3.3", "4.4.4.4", 2000, 443, "TCP", 300)
        assert len(agg.flows) == 2


# --------------------------------------------------------------------------- #
# 3. Flush — calculul caracteristicilor                                        #
# --------------------------------------------------------------------------- #
class TestFlush:

    def test_flush_returneaza_toate_campurile(self):
        agg = FlowAggregator()
        agg.add_packet("1.1.1.1", "2.2.2.2", 1000, 80, "TCP", 500,
                       syn=True, ack=True, is_forward=True)
        flows = agg.flush()
        assert len(flows) == 1
        expected_keys = {
            "sourceIp", "destinationIp", "sourcePort", "destinationPort", "protocol",
            "totalFwdPackets", "totalBwdPackets", "totalFwdBytes", "totalBwdBytes",
            "flowDuration", "flowBytesPerSec", "flowPacketsPerSec",
            "synFlagCount", "rstFlagCount", "avgPacketSize",
            "finFlagCount", "ackFlagCount", "pshFlagCount", "urgFlagCount",
            "fwdPacketLenMin", "fwdPacketLenMax", "bwdPacketLenMax", "packetLenStd",
        }
        assert expected_keys == set(flows[0].keys())

    def test_flush_goleste_fluxurile(self):
        agg = FlowAggregator()
        agg.add_packet("1.1.1.1", "2.2.2.2", 1000, 80, "TCP", 500)
        agg.flush()
        assert len(agg.flows) == 0

    def test_flush_pe_agregator_gol(self):
        agg = FlowAggregator()
        assert agg.flush() == []

    def test_bytes_per_sec_pozitiv(self):
        agg = FlowAggregator()
        agg.add_packet("1.1.1.1", "2.2.2.2", 1000, 80, "TCP", 1000, is_forward=True)
        flows = agg.flush()
        assert flows[0]["flowBytesPerSec"] > 0

    def test_avg_packet_size_corect(self):
        agg = FlowAggregator()
        agg.add_packet("1.1.1.1", "2.2.2.2", 1000, 80, "TCP", 100, is_forward=True)
        agg.add_packet("1.1.1.1", "2.2.2.2", 1000, 80, "TCP", 300, is_forward=True)
        flows = agg.flush()
        assert flows[0]["avgPacketSize"] == pytest.approx(200.0)

    def test_packet_std_zero_pentru_un_pachet(self):
        agg = FlowAggregator()
        agg.add_packet("1.1.1.1", "2.2.2.2", 1000, 80, "TCP", 500)
        flows = agg.flush()
        assert flows[0]["packetLenStd"] == 0.0

    def test_packet_std_nenul_pentru_pachete_multiple(self):
        agg = FlowAggregator()
        agg.add_packet("1.1.1.1", "2.2.2.2", 1000, 80, "TCP", 100)
        agg.add_packet("1.1.1.1", "2.2.2.2", 1000, 80, "TCP", 900)
        flows = agg.flush()
        assert flows[0]["packetLenStd"] > 0

    def test_fwd_bwd_max_corecte(self):
        agg = FlowAggregator()
        agg.add_packet("1.1.1.1", "2.2.2.2", 1000, 80, "TCP", 400, is_forward=True)
        agg.add_packet("1.1.1.1", "2.2.2.2", 1000, 80, "TCP", 600, is_forward=True)
        agg.add_packet("1.1.1.1", "2.2.2.2", 1000, 80, "TCP", 250, is_forward=False)
        flows = agg.flush()
        assert flows[0]["fwdPacketLenMax"] == 600
        assert flows[0]["bwdPacketLenMax"] == 250


# --------------------------------------------------------------------------- #
# 4. Praguri de detecție rapidă                                                #
# --------------------------------------------------------------------------- #
class TestRapidThresholds:

    def test_prag_syn_definit(self):
        assert RAPID_SYN_THRESHOLD == 50

    def test_prag_flood_definit(self):
        assert RAPID_FLOOD_BYTES == 2_000_000

    def test_flux_cu_syn_peste_prag(self):
        agg = FlowAggregator()
        for _ in range(RAPID_SYN_THRESHOLD):
            agg.add_packet("10.0.0.99", "192.168.1.1",
                           40000, 22, "TCP", 64, syn=True)
        key = agg._canonical_key("10.0.0.99", "192.168.1.1", 40000, 22, "TCP")
        assert agg.flows[key].syn_count >= RAPID_SYN_THRESHOLD
