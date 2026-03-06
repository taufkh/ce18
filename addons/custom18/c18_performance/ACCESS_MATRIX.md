# C18 Performance Demo Access Matrix

Database reference: `demo`

## Demo users

| Level | Login | Password | Employee | Department | Performance group |
| --- | --- | --- | --- | --- | --- |
| Management | `c18.management` | `demo123` | Sharlene Rhodes | Management | Executive |
| Manager | `c18.hr.manager` | `demo123` | Tina Williamson | Administration | Manager |
| Supervisor | `c18.rd.supervisor` | `demo123` | Ronnie Hart | Research & Development | Manager |
| Staff | `c18.project.staff` | `demo123` | Paul Williams | Long Term Projects | User |

## Group mapping

| Level | `group_c18_performance_user` | `group_c18_performance_manager` | `group_c18_performance_executive` |
| --- | --- | --- | --- |
| Management | Yes | Yes | Yes |
| Manager | Yes | Yes | No |
| Supervisor | Yes | Yes | No |
| Staff | Yes | No | No |

Manager implies User. Executive implies Manager and User.

## Menu visibility

| Menu | Staff | Supervisor | Manager | Management |
| --- | --- | --- | --- | --- |
| Staff Board | Yes | Yes | Yes | Yes |
| Manager Board | No | Yes | Yes | Yes |
| Executive Board | No | No | No | Yes |
| My Objectives | Yes | Yes | Yes | Yes |
| My KPIs | Yes | Yes | Yes | Yes |
| My Check-ins | Yes | Yes | Yes | Yes |
| My Department Objectives | No | Yes | Yes | Yes |
| My Department KPIs | No | Yes | Yes | Yes |
| My Department Check-ins | No | Yes | Yes | Yes |
| Overdue Check-ins | Yes | Yes | Yes | Yes |

## Sample POV data

| Login | Primary owned objective | Primary owned KPI examples |
| --- | --- | --- |
| `c18.management` | `Strengthen Portfolio Governance` | `Priority Initiative Approval`, `Quarterly Strategy Review Completion` |
| `c18.hr.manager` | `Improve Workforce Readiness` | `Training Plan Completion`, `Hiring Readiness Index` |
| `c18.rd.supervisor` | `Increase R&D Delivery Predictability` | `Production Bug Escape Reduction`, `Sprint Delivery Predictability` |
| `c18.project.staff` | `Deliver Long-Term Project Milestones` | `Resolved Defects per Iteration`, `Milestone Completion Rate` |

## Approval flow

1. Staff/user submits KPI check-in.
2. Check-in starts in `Pending`.
3. Manager or Executive can `Approve` or `Reject`.
4. Objective cannot be locked while related check-ins are still `Pending`.

## Notes

- Some extra technical groups shown on demo users come from Odoo core `Internal User` implications, not from `c18_performance`.
- Performance access mapping should be evaluated from the `C18 Performance User/Manager/Executive` groups and the role-specific menus above.
