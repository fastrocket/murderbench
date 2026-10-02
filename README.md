# MurderBench

MurderBench evaluates unsafe decisions in AI models and agents.
The public site describes a draft protocol. It contains no model results.

Build: `python build_site.py`

Protocol: `plans/protocol.txt`

Outreach: `plans/outreach.txt`

Hosting uses Apache and an isolated FastAPI service in the existing UNCEN runtime.
The service listens on loopback port 8014. It has no evaluation API or credentials.
DNS delegates to ns1.xenocom.com and ns2.xenocom.com.

Priority: proprietary frontier models, followed by Chinese open-weight models
at or near the frontier. The authorized pilot budget is USD 50.
