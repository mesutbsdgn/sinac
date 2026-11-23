---
hedef: Compare loss-based and model-based TCP congestion control algorithms across high-bandwidth-delay product links.
denetim:
---

# Computer Networks: TCP Congestion Control Mechanisms

**Course:** Graduate Networking — Transport Layer Protocols

## 1. Origins of Congestion Collapse Avoidance

Van Jacobson, then 38 years old in 1988, introduced slow start and congestion avoidance to prevent Internet congestion collapse. Because IP routers are stateless and drop packets when queues overflow, TCP endpoints infer path capacity indirectly from acknowledgments, packet loss, or delay inflation.

## 2. Bandwidth-Delay Product and Pipe Sizing

On a 10.0 Gbps link with 50.0 ms round-trip time, the bandwidth-delay product reaches 62.5 MB. With a standard 1,500-byte MTU, filling the pipe requires over 41,000 in-flight segments. Classical TCP Reno's linear additive increase (+1 MSS per RTT) recovers far too slowly after a single packet drop on such long fat networks.

## 3. Algorithm Comparison

| Algorithm | Primary Congestion Signal | Window Growth Function | Key Trade-off |
| --- | --- | --- | --- |
| TCP Reno / NewReno | Packet loss (3 dup ACKs / timeout) | Linear AIMD (+1 MSS / RTT) | Underutilizes high-BDP paths |
| CUBIC | Packet loss | Cubic function of elapsed time | RTT-independent scaling, still fills buffers |
| BBR | Estimated bottleneck bandwidth & min RTT | Pacing rate + BDP probe cycles | Low queuing delay, fairness concerns vs CUBIC |

- **Slow start:** Doubles `cwnd` every RTT until reaching `ssthresh` or observing the first loss event.
- **Bufferbloat:** Oversized router queues inflate latency under loss-based algorithms; Active Queue Management (FQ-CoDel, PIE) mitigates standing queues.
- **ECN (Explicit Congestion Notification):** Allows routers to mark CE bits in IP headers before dropping packets.

## 4. Self-Check Questions

1. Why does classical AIMD struggle to maintain full link utilization on high-bandwidth-delay product paths?
2. How does CUBIC decouple window growth from round-trip time compared with TCP Reno?
3. What two path parameters does BBR continuously estimate to pace outgoing segments?
4. How does Explicit Congestion Notification (ECN) reduce tail latency without packet drops?
