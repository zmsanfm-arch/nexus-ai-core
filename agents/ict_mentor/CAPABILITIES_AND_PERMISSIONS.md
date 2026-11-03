# ICT Mentor Capabilities and Permissions

## Enabled capabilities
- ict.education
- ict.source_lookup
- ict.chart_analysis
- ict.strategy_formalization
- ict.trade_review

## Defined but disabled
- ict.position_monitoring
- ict.position_management
- ict.autonomous_execution

These are roadmap definitions only and must not be registered as active/routable capabilities in this release.

## Permission requests
- knowledge.retrieve
- user_input.read
- chart_attachment.read

These are requests, not grants; NEXUS centrally enforces actual authorization.

## Not granted
- Live market, account, or position read access
- Position modification
- Order submission or cancellation
- MT5 or broker connectivity
- Broker credentials or secrets
- Risk-policy modification
- Governance or approval bypass

No tool permission is implied by an analytical capability. Chart analysis and trade review never authorize execution.
