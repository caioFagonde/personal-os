# Optional Makefile targets for AgentOps. Append manually if desired.
agent-doctor:
	python3 scripts/agents/agentctl.py doctor

agent-list:
	python3 scripts/agents/agentctl.py list

agent-status:
	python3 scripts/agents/agentctl.py status

agent-monitor:
	scripts/agents/monitor.sh

agent-collect:
	python3 scripts/agents/agentctl.py collect
