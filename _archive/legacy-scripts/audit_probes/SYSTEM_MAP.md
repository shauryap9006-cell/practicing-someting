# RailTwin-X System Map (Phase 0 Deep Due Diligence)

Generated via dynamic code reflection and static AST verification.
Repository Root: `C:\Users\shaur\OneDrive\web2\sih`

## 0.1 Route Inventory & Unmounted Route Cross-Check
- **Total Mounted Endpoints:** 214
- **Total Declared in `api/*.py`:** 162
- **Unmounted Routes (Dead Code):** 0

> [!NOTE]
> **Zero unmounted routes.** All 162 route handler functions declared across the 22 `api/*_routes.py` files are mounted in `api/main.py` via `ROUTER_MANIFEST` or direct `include_router` bindings.


### Complete Route Table
| Method | Path | Auth | Async/Sync | Handler | Location |
|---|---|---|---|---|---|
| `GET` | `/` | NO | `sync` | `root_redirect` | `api\main.py:273` |
| `POST` | `/api/access-requests` | NO | `sync` | `create_access_request` | `api\access_routes.py:30` |
| `GET` | `/api/admin/access-requests` | YES | `sync` | `list_access_requests` | `api\admin_routes.py:81` |
| `PUT` | `/api/admin/access-requests/{request_id}` | YES | `sync` | `review_access_request` | `api\admin_routes.py:102` |
| `GET` | `/api/admin/backups` | YES | `sync` | `list_backups` | `api\admin_routes.py:348` |
| `POST` | `/api/admin/backups/create` | YES | `sync` | `trigger_backup` | `api\admin_routes.py:382` |
| `POST` | `/api/admin/backups/verify` | YES | `sync` | `verify_latest_backup` | `api\admin_routes.py:401` |
| `GET` | `/api/admin/users` | YES | `sync` | `list_users` | `api\admin_routes.py:138` |
| `POST` | `/api/admin/users` | YES | `sync` | `create_user` | `api\admin_routes.py:176` |
| `PUT` | `/api/admin/users/{user_id}` | YES | `sync` | `update_user` | `api\admin_routes.py:254` |
| `GET` | `/api/audit/logs` | YES | `sync` | `get_audit_logs` | `api\audit_routes.py:48` |
| `GET` | `/api/audit/verify-integrity` | YES | `sync` | `verify_audit_trail_integrity` | `api\audit_routes.py:106` |
| `POST` | `/api/auth/login` | NO | `sync` | `login` | `api\auth_routes.py:54` |
| `POST` | `/api/auth/logout` | NO | `sync` | `logout` | `api\auth_routes.py:228` |
| `GET` | `/api/auth/me` | YES | `sync` | `get_current_user_profile` | `api\auth_routes.py:141` |
| `POST` | `/api/auth/refresh` | NO | `sync` | `refresh_token` | `api\auth_routes.py:156` |
| `GET` | `/api/blocks/status` | YES | `sync` | `get_block_statuses` | `api\block_routes.py:34` |
| `POST` | `/api/blocks/{block_id}/line-clear` | YES | `sync` | `grant_line_clear` | `api\block_routes.py:145` |
| `POST` | `/api/blocks/{block_id}/state` | YES | `sync` | `update_block_state` | `api\block_routes.py:104` |
| `GET` | `/api/board/kiosk` | NO | `sync` | `get_kiosk_board` | `api\board_routes.py:209` |
| `GET` | `/api/board/live` | YES | `sync` | `get_live_board` | `api\board_routes.py:39` |
| `GET` | `/api/board/stream` | NO | `async` | `stream_live_board` | `api\board_routes.py:257` |
| `GET` | `/api/commercial/announcements/generate` | NO | `sync` | `generate_platform_announcement` | `api\commercial_routes.py:179` |
| `POST` | `/api/commercial/delay-certificate` | YES | `sync` | `issue_delay_certificate` | `api\commercial_routes.py:39` |
| `GET` | `/api/commercial/delay-certificate/verify/{qr_token}` | NO | `sync` | `verify_delay_certificate` | `api\commercial_routes.py:148` |
| `GET` | `/api/commercial/delay-certificate/{cert_no}` | YES | `sync` | `get_delay_certificate` | `api\commercial_routes.py:132` |
| `GET` | `/api/commercial/lost-found` | YES | `sync` | `list_lost_items` | `api\commercial_routes.py:426` |
| `POST` | `/api/commercial/lost-found` | YES | `sync` | `register_lost_item` | `api\commercial_routes.py:382` |
| `PUT` | `/api/commercial/lost-found/{item_id}/claim` | YES | `sync` | `claim_lost_item` | `api\commercial_routes.py:453` |
| `GET` | `/api/commercial/stalls` | YES | `sync` | `list_commercial_stalls` | `api\commercial_routes.py:314` |
| `POST` | `/api/commercial/stalls` | YES | `sync` | `register_commercial_stall` | `api\commercial_routes.py:264` |
| `GET` | `/api/coordination/advisories/generate` | YES | `sync` | `generate_precedence_advisories` | `api\section_routes.py:239` |
| `POST` | `/api/coordination/advisories/{adv_id}/execute` | YES | `sync` | `execute_precedence_advisory` | `api\section_routes.py:283` |
| `GET` | `/api/coordination/corridor` | YES | `sync` | `get_corridor_topology` | `api\section_routes.py:37` |
| `GET` | `/api/coordination/dfc` | YES | `sync` | `get_dfc_precedence` | `api\section_routes.py:315` |
| `POST` | `/api/coordination/handoff/request` | YES | `sync` | `request_cross_station_handoff` | `api\section_routes.py:80` |
| `PUT` | `/api/coordination/handoff/{lock_id}/grant` | YES | `sync` | `grant_cross_station_handoff` | `api\section_routes.py:131` |
| `PUT` | `/api/coordination/handoff/{lock_id}/release` | YES | `sync` | `release_cross_station_handoff` | `api\section_routes.py:169` |
| `GET` | `/api/coordination/handoffs` | YES | `sync` | `list_cross_station_handoffs` | `api\section_routes.py:206` |
| `GET` | `/api/coordination/precedence` | YES | `sync` | `generate_precedence_advisories` | `api\section_routes.py:239` |
| `GET` | `/api/handover/current` | YES | `sync` | `get_current_handover_summary` | `api\handover_routes.py:138` |
| `POST` | `/api/handover/draft` | YES | `sync` | `create_or_update_draft` | `api\handover_routes.py:165` |
| `GET` | `/api/handover/history` | YES | `sync` | `list_handover_history` | `api\handover_routes.py:370` |
| `POST` | `/api/handover/{handover_id}/ack-in` | YES | `sync` | `acknowledge_incoming_shift` | `api\handover_routes.py:310` |
| `POST` | `/api/handover/{handover_id}/sign-out` | YES | `sync` | `sign_out_shift` | `api\handover_routes.py:257` |
| `GET` | `/api/infra/assets` | YES | `sync` | `list_station_assets` | `api\infra_routes.py:197` |
| `POST` | `/api/infra/assets` | YES | `sync` | `register_station_asset` | `api\infra_routes.py:151` |
| `GET` | `/api/infra/cleaning-logs` | YES | `sync` | `list_cleaning_logs` | `api\infra_routes.py:441` |
| `POST` | `/api/infra/cleaning-logs` | YES | `sync` | `record_cleaning_log` | `api\infra_routes.py:407` |
| `GET` | `/api/infra/feedback` | YES | `sync` | `list_cleaning_logs` | `api\infra_routes.py:441` |
| `GET` | `/api/infra/rakes` | YES | `sync` | `list_rakes` | `api\infra_routes.py:91` |
| `POST` | `/api/infra/rakes` | YES | `sync` | `register_rake_bpc` | `api\infra_routes.py:41` |
| `GET` | `/api/infra/work-orders` | YES | `sync` | `list_work_orders` | `api\infra_routes.py:319` |
| `POST` | `/api/infra/work-orders` | YES | `sync` | `create_work_order` | `api\infra_routes.py:259` |
| `PUT` | `/api/infra/work-orders/{wo_id}/resolve` | YES | `sync` | `resolve_work_order` | `api\infra_routes.py:350` |
| `GET` | `/api/infrastructure/assets` | YES | `sync` | `list_station_assets` | `api\infra_routes.py:197` |
| `POST` | `/api/infrastructure/assets` | YES | `sync` | `register_station_asset` | `api\infra_routes.py:151` |
| `GET` | `/api/infrastructure/cleaning-logs` | YES | `sync` | `list_cleaning_logs` | `api\infra_routes.py:441` |
| `POST` | `/api/infrastructure/cleaning-logs` | YES | `sync` | `record_cleaning_log` | `api\infra_routes.py:407` |
| `GET` | `/api/infrastructure/feedback` | YES | `sync` | `list_cleaning_logs` | `api\infra_routes.py:441` |
| `GET` | `/api/infrastructure/rakes` | YES | `sync` | `list_rakes` | `api\infra_routes.py:91` |
| `POST` | `/api/infrastructure/rakes` | YES | `sync` | `register_rake_bpc` | `api\infra_routes.py:41` |
| `GET` | `/api/infrastructure/work-orders` | YES | `sync` | `list_work_orders` | `api\infra_routes.py:319` |
| `POST` | `/api/infrastructure/work-orders` | YES | `sync` | `create_work_order` | `api\infra_routes.py:259` |
| `PUT` | `/api/infrastructure/work-orders/{wo_id}/resolve` | YES | `sync` | `resolve_work_order` | `api\infra_routes.py:350` |
| `GET` | `/api/notifications/active` | YES | `sync` | `get_active_notifications` | `api\notification_routes.py:58` |
| `POST` | `/api/notifications/emit` | YES | `sync` | `emit_notification_endpoint` | `api\notification_routes.py:155` |
| `POST` | `/api/notifications/escalate` | YES | `sync` | `trigger_escalation_ladder` | `api\notification_routes.py:189` |
| `POST` | `/api/notifications/{notification_id}/ack` | YES | `sync` | `ack_notification_endpoint` | `api\notification_routes.py:113` |
| `GET` | `/api/ops/ad-events` | YES | `sync` | `list_ad_events` | `api\ops_routes.py:240` |
| `POST` | `/api/ops/setin/{train_no}` | YES | `sync` | `record_set_in` | `api\ops_routes.py:55` |
| `POST` | `/api/ops/setout/{train_no}` | YES | `sync` | `record_set_out` | `api\ops_routes.py:157` |
| `GET` | `/api/ops/shunting` | YES | `sync` | `list_shunting_moves` | `api\ops_routes.py:356` |
| `POST` | `/api/ops/shunting` | YES | `sync` | `create_shunting_move` | `api\ops_routes.py:287` |
| `PUT` | `/api/ops/shunting/{move_id}/status` | YES | `sync` | `update_shunting_status` | `api\ops_routes.py:403` |
| `POST` | `/api/planner/apply` | YES | `sync` | `apply_day_changeset` | `api\planner_routes.py:100` |
| `GET` | `/api/planner/changesets` | YES | `sync` | `list_planner_changesets` | `api\planner_routes.py:176` |
| `POST` | `/api/planner/simulate` | YES | `sync` | `simulate_day_changeset` | `api\planner_routes.py:41` |
| `POST` | `/api/platform/assign` | YES | `sync` | `assign_platform` | `api\platform_routes.py:148` |
| `POST` | `/api/platform/assignments/{assign_id}/lock` | YES | `sync` | `toggle_assignment_lock` | `api\platform_routes.py:243` |
| `POST` | `/api/platform/block` | YES | `sync` | `set_platform_block` | `api\platform_routes.py:90` |
| `POST` | `/api/platform/reoptimize` | YES | `sync` | `reoptimize_station_platforms` | `api\platform_routes.py:285` |
| `GET` | `/api/platform/states` | YES | `sync` | `get_platform_states` | `api\platform_routes.py:45` |
| `GET` | `/api/safety/incidents` | YES | `sync` | `list_incidents` | `api\safety_routes.py:476` |
| `POST` | `/api/safety/incidents` | YES | `sync` | `report_incident` | `api\safety_routes.py:419` |
| `GET` | `/api/safety/lc/status` | YES | `sync` | `list_level_crossings` | `api\safety_routes.py:708` |
| `PUT` | `/api/safety/lc/{lc_id}/status` | YES | `sync` | `update_lc_status` | `api\safety_routes.py:753` |
| `POST` | `/api/safety/possession/request` | YES | `sync` | `request_possession` | `api\safety_routes.py:187` |
| `POST` | `/api/safety/possession/{possession_id}/grant` | YES | `sync` | `grant_possession` | `api\safety_routes.py:233` |
| `POST` | `/api/safety/possession/{possession_id}/restore` | YES | `sync` | `restore_possession` | `api\safety_routes.py:314` |
| `GET` | `/api/safety/possessions` | YES | `sync` | `list_possessions` | `api\safety_routes.py:379` |
| `GET` | `/api/safety/sop/active` | YES | `sync` | `list_active_sop_runs` | `api\safety_routes.py:675` |
| `POST` | `/api/safety/sop/start` | YES | `sync` | `start_sop_run` | `api\safety_routes.py:556` |
| `GET` | `/api/safety/sop/templates` | NO | `sync` | `get_sop_templates` | `api\safety_routes.py:545` |
| `POST` | `/api/safety/sop/{run_id}/step` | YES | `sync` | `complete_sop_step` | `api\safety_routes.py:617` |
| `GET` | `/api/safety/tsr` | YES | `sync` | `list_speed_restrictions` | `api\safety_routes.py:115` |
| `POST` | `/api/safety/tsr` | YES | `sync` | `create_speed_restriction` | `api\safety_routes.py:43` |
| `DELETE` | `/api/safety/tsr/{tsr_id}` | YES | `sync` | `cancel_speed_restriction` | `api\safety_routes.py:142` |
| `GET` | `/api/section/advisories/generate` | YES | `sync` | `generate_precedence_advisories` | `api\section_routes.py:239` |
| `POST` | `/api/section/advisories/{adv_id}/execute` | YES | `sync` | `execute_precedence_advisory` | `api\section_routes.py:283` |
| `GET` | `/api/section/corridor` | YES | `sync` | `get_corridor_topology` | `api\section_routes.py:37` |
| `GET` | `/api/section/dfc` | YES | `sync` | `get_dfc_precedence` | `api\section_routes.py:315` |
| `POST` | `/api/section/handoff/request` | YES | `sync` | `request_cross_station_handoff` | `api\section_routes.py:80` |
| `PUT` | `/api/section/handoff/{lock_id}/grant` | YES | `sync` | `grant_cross_station_handoff` | `api\section_routes.py:131` |
| `PUT` | `/api/section/handoff/{lock_id}/release` | YES | `sync` | `release_cross_station_handoff` | `api\section_routes.py:169` |
| `GET` | `/api/section/handoffs` | YES | `sync` | `list_cross_station_handoffs` | `api\section_routes.py:206` |
| `GET` | `/api/section/precedence` | YES | `sync` | `generate_precedence_advisories` | `api\section_routes.py:239` |
| `GET` | `/api/system/model-info` | NO | `sync` | `get_system_model_info` | `api\system_routes.py:89` |
| `GET` | `/api/system/status` | NO | `sync` | `get_system_status` | `api\system_routes.py:20` |
| `POST` | `/api/timetable/entries` | YES | `sync` | `create_timetable_entry` | `api\timetable_routes.py:209` |
| `DELETE` | `/api/timetable/entries/{entry_id}` | YES | `sync` | `delete_timetable_entry` | `api\timetable_routes.py:323` |
| `PUT` | `/api/timetable/entries/{entry_id}` | YES | `sync` | `update_timetable_entry` | `api\timetable_routes.py:264` |
| `GET` | `/api/timetable/versions` | YES | `sync` | `list_timetable_versions` | `api\timetable_routes.py:59` |
| `POST` | `/api/timetable/versions` | YES | `sync` | `create_timetable_version` | `api\timetable_routes.py:99` |
| `GET` | `/api/timetable/versions/{version_id}/entries` | YES | `sync` | `get_version_entries` | `api\timetable_routes.py:150` |
| `POST` | `/api/timetable/versions/{version_id}/import-seed` | YES | `sync` | `import_seed_timetable` | `api\timetable_routes.py:394` |
| `POST` | `/api/timetable/versions/{version_id}/publish` | YES | `sync` | `publish_timetable_version` | `api\timetable_routes.py:450` |
| `GET` | `/api/timetable/versions/{version_id}/validate` | YES | `sync` | `validate_timetable_version` | `api\timetable_routes.py:352` |
| `POST` | `/api/v1/advise` | YES | `sync` | `post_brain_advise` | `api\routes.py:965` |
| `POST` | `/api/v1/advise/{adv_id}/ack` | YES | `sync` | `post_advisory_ack` | `api\routes.py:1067` |
| `GET` | `/api/v1/cascade/ripple` | NO | `sync` | `get_cascade_ripple` | `api\demo_routes.py:339` |
| `GET` | `/api/v1/conflicts/{train_no}` | NO | `sync` | `get_train_conflicts` | `api\routes.py:983` |
| `GET` | `/api/v1/crew/alerts` | NO | `sync` | `get_crew_alerts` | `api\routes.py:821` |
| `GET` | `/api/v1/demo/comparator` | NO | `sync` | `get_demo_comparator` | `api\demo_routes.py:88` |
| `POST` | `/api/v1/demo/inject-event` | NO | `sync` | `inject_shock_event` | `api\demo_routes.py:53` |
| `POST` | `/api/v1/demo/reset-events` | NO | `sync` | `reset_shock_events` | `api\demo_routes.py:75` |
| `GET` | `/api/v1/demo/shocks` | NO | `sync` | `get_active_shocks` | `api\demo_routes.py:42` |
| `GET` | `/api/v1/demo/time-machine` | NO | `sync` | `get_demo_time_machine` | `api\demo_routes.py:456` |
| `GET` | `/api/v1/evaluation/summary` | NO | `sync` | `get_evaluation_summary` | `api\routes.py:45` |
| `GET` | `/api/v1/health` | NO | `sync` | `get_health` | `api\routes.py:1207` |
| `POST` | `/api/v1/hooks/whatsapp` | NO | `async` | `whatsapp_inbound_webhook` | `api\routes.py:1109` |
| `GET` | `/api/v1/ledger/scoreboard` | NO | `sync` | `get_prediction_ledger_scoreboard` | `api\routes.py:874` |
| `GET` | `/api/v1/ledger/verify` | NO | `sync` | `verify_prediction_ledger_chain` | `api\routes.py:886` |
| `GET` | `/api/v1/live/positions` | NO | `sync` | `get_live_positions` | `api\live_routes.py:256` |
| `GET` | `/api/v1/live/stream` | NO | `async` | `stream_live_positions` | `api\live_routes.py:275` |
| `GET` | `/api/v1/meta/config` | NO | `sync` | `get_meta_config` | `api\live_routes.py:46` |
| `GET` | `/api/v1/meta/models` | NO | `sync` | `get_models_meta` | `api\routes.py:904` |
| `GET` | `/api/v1/meta/stations` | NO | `sync` | `get_meta_stations` | `api\routes.py:929` |
| `GET` | `/api/v1/meta/trains` | NO | `sync` | `get_meta_trains` | `api\routes.py:947` |
| `GET` | `/api/v1/model/performance` | NO | `sync` | `get_model_performance` | `api\routes.py:66` |
| `GET` | `/api/v1/network/state` | NO | `sync` | `get_network_state` | `api\routes.py:494` |
| `GET` | `/api/v1/passenger/pnr/{pnr}` | NO | `sync` | `get_pnr` | `api\passenger_routes.py:454` |
| `GET` | `/api/v1/passenger/popular` | NO | `sync` | `get_popular_trains` | `api\passenger_routes.py:330` |
| `GET` | `/api/v1/passenger/search` | NO | `sync` | `search_trains` | `api\passenger_routes.py:241` |
| `GET` | `/api/v1/passenger/search` | NO | `sync` | `passenger_search` | `api\routes.py:450` |
| `GET` | `/api/v1/passenger/snapshot` | NO | `sync` | `get_passenger_snapshot` | `api\passenger_routes.py:470` |
| `GET` | `/api/v1/passenger/stream` | NO | `async` | `stream_passenger_train` | `api\passenger_routes.py:156` |
| `GET` | `/api/v1/pnr/{pnr_no}` | NO | `sync` | `get_pnr_status` | `api\routes.py:314` |
| `POST` | `/api/v1/simulate/what-if` | YES | `sync` | `simulate_what_if` | `api\routes.py:764` |
| `GET` | `/api/v1/stations/{code}` | NO | `sync` | `get_station_summary` | `api\routes.py:643` |
| `GET` | `/api/v1/stations/{code}/connections` | NO | `sync` | `get_station_connections` | `api\routes.py:840` |
| `GET` | `/api/v1/stations/{code}/gantt` | NO | `sync` | `get_station_gantt` | `api\routes.py:701` |
| `POST` | `/api/v1/stations/{code}/reoptimize` | YES | `sync` | `reoptimize_station_platforms` | `api\routes.py:732` |
| `GET` | `/api/v1/trains/{train_no}/autopsy` | NO | `sync` | `get_train_autopsy` | `api\routes.py:276` |
| `GET` | `/api/v1/trains/{train_no}/eta` | NO | `sync` | `get_train_eta` | `api\routes.py:146` |
| `GET` | `/api/v1/trains/{train_no}/journey` | NO | `sync` | `get_train_journey` | `api\routes.py:165` |
| `GET` | `/api/v1/trains/{train_no}/live` | NO | `sync` | `get_train_live` | `api\live_routes.py:96` |
| `GET` | `/api/v1/trains/{train_no}/why-late` | NO | `sync` | `get_train_why_late` | `api\live_routes.py:201` |
| `GET` | `/api/workforce/breathalyzer` | YES | `sync` | `list_breathalyzer_tests` | `api\workforce_routes.py:111` |
| `POST` | `/api/workforce/breathalyzer` | YES | `sync` | `record_breathalyzer_test` | `api\workforce_routes.py:39` |
| `GET` | `/api/workforce/crew/breaches` | YES | `sync` | `check_crew_breaches` | `api\workforce_routes.py:320` |
| `GET` | `/api/workforce/crew/roster` | YES | `sync` | `list_crew_roster` | `api\workforce_routes.py:255` |
| `POST` | `/api/workforce/crew/sign-on` | YES | `sync` | `crew_sign_on` | `api\workforce_routes.py:142` |
| `POST` | `/api/workforce/crew/{roster_id}/sign-off` | YES | `sync` | `crew_sign_off` | `api\workforce_routes.py:203` |
| `GET` | `/api/workforce/sahayak` | YES | `sync` | `list_sahayak_roster` | `api\workforce_routes.py:441` |
| `PUT` | `/api/workforce/sahayak/{sahayak_id}/duty` | YES | `sync` | `toggle_sahayak_duty` | `api\workforce_routes.py:491` |
| `GET` | `/api/workforce/shifts` | YES | `sync` | `list_staff_shifts` | `api\workforce_routes.py:387` |
| `POST` | `/api/workforce/shifts` | YES | `sync` | `assign_staff_shift` | `api\workforce_routes.py:344` |
| `GET,HEAD` | `/docs` | NO | `async` | `swagger_ui_html` | `unknown` |
| `GET,HEAD` | `/docs/oauth2-redirect` | NO | `async` | `swagger_ui_redirect` | `unknown` |
| `GET` | `/healthz` | NO | `sync` | `liveness_probe` | `api\main.py:260` |
| `GET,HEAD` | `/openapi.json` | NO | `async` | `openapi` | `unknown` |
| `GET` | `/readyz` | NO | `sync` | `readiness_probe` | `api\main.py:266` |
| `GET,HEAD` | `/redoc` | NO | `async` | `redoc_html` | `unknown` |
| `POST` | `/v1/advise` | YES | `sync` | `post_brain_advise` | `api\routes.py:965` |
| `POST` | `/v1/advise/{adv_id}/ack` | YES | `sync` | `post_advisory_ack` | `api\routes.py:1067` |
| `GET` | `/v1/cascade/ripple` | NO | `sync` | `get_cascade_ripple` | `api\demo_routes.py:339` |
| `GET` | `/v1/conflicts/{train_no}` | NO | `sync` | `get_train_conflicts` | `api\routes.py:983` |
| `GET` | `/v1/crew/alerts` | NO | `sync` | `get_crew_alerts` | `api\routes.py:821` |
| `GET` | `/v1/demo/comparator` | NO | `sync` | `get_demo_comparator` | `api\demo_routes.py:88` |
| `POST` | `/v1/demo/inject-event` | NO | `sync` | `inject_shock_event` | `api\demo_routes.py:53` |
| `POST` | `/v1/demo/reset-events` | NO | `sync` | `reset_shock_events` | `api\demo_routes.py:75` |
| `GET` | `/v1/demo/shocks` | NO | `sync` | `get_active_shocks` | `api\demo_routes.py:42` |
| `GET` | `/v1/demo/time-machine` | NO | `sync` | `get_demo_time_machine` | `api\demo_routes.py:456` |
| `GET` | `/v1/evaluation/summary` | NO | `sync` | `get_evaluation_summary` | `api\routes.py:45` |
| `GET` | `/v1/health` | NO | `sync` | `get_health` | `api\routes.py:1207` |
| `POST` | `/v1/hooks/whatsapp` | NO | `async` | `whatsapp_inbound_webhook` | `api\routes.py:1109` |
| `GET` | `/v1/ledger/scoreboard` | NO | `sync` | `get_prediction_ledger_scoreboard` | `api\routes.py:874` |
| `GET` | `/v1/ledger/verify` | NO | `sync` | `verify_prediction_ledger_chain` | `api\routes.py:886` |
| `GET` | `/v1/live/positions` | NO | `sync` | `get_live_positions` | `api\live_routes.py:256` |
| `GET` | `/v1/live/stream` | NO | `async` | `stream_live_positions` | `api\live_routes.py:275` |
| `GET` | `/v1/meta/config` | NO | `sync` | `get_meta_config` | `api\live_routes.py:46` |
| `GET` | `/v1/meta/models` | NO | `sync` | `get_models_meta` | `api\routes.py:904` |
| `GET` | `/v1/meta/stations` | NO | `sync` | `get_meta_stations` | `api\routes.py:929` |
| `GET` | `/v1/meta/trains` | NO | `sync` | `get_meta_trains` | `api\routes.py:947` |
| `GET` | `/v1/model/performance` | NO | `sync` | `get_model_performance` | `api\routes.py:66` |
| `GET` | `/v1/network/state` | NO | `sync` | `get_network_state` | `api\routes.py:494` |
| `GET` | `/v1/passenger/pnr/{pnr}` | NO | `sync` | `get_pnr` | `api\passenger_routes.py:454` |
| `GET` | `/v1/passenger/popular` | NO | `sync` | `get_popular_trains` | `api\passenger_routes.py:330` |
| `GET` | `/v1/passenger/search` | NO | `sync` | `search_trains` | `api\passenger_routes.py:241` |
| `GET` | `/v1/passenger/search` | NO | `sync` | `passenger_search` | `api\routes.py:450` |
| `GET` | `/v1/passenger/snapshot` | NO | `sync` | `get_passenger_snapshot` | `api\passenger_routes.py:470` |
| `GET` | `/v1/passenger/stream` | NO | `async` | `stream_passenger_train` | `api\passenger_routes.py:156` |
| `GET` | `/v1/pnr/{pnr_no}` | NO | `sync` | `get_pnr_status` | `api\routes.py:314` |
| `POST` | `/v1/simulate/what-if` | YES | `sync` | `simulate_what_if` | `api\routes.py:764` |
| `GET` | `/v1/stations/{code}` | NO | `sync` | `get_station_summary` | `api\routes.py:643` |
| `GET` | `/v1/stations/{code}/connections` | NO | `sync` | `get_station_connections` | `api\routes.py:840` |
| `GET` | `/v1/stations/{code}/gantt` | NO | `sync` | `get_station_gantt` | `api\routes.py:701` |
| `POST` | `/v1/stations/{code}/reoptimize` | YES | `sync` | `reoptimize_station_platforms` | `api\routes.py:732` |
| `GET` | `/v1/trains/{train_no}/autopsy` | NO | `sync` | `get_train_autopsy` | `api\routes.py:276` |
| `GET` | `/v1/trains/{train_no}/eta` | NO | `sync` | `get_train_eta` | `api\routes.py:146` |
| `GET` | `/v1/trains/{train_no}/journey` | NO | `sync` | `get_train_journey` | `api\routes.py:165` |
| `GET` | `/v1/trains/{train_no}/live` | NO | `sync` | `get_train_live` | `api\live_routes.py:96` |
| `GET` | `/v1/trains/{train_no}/why-late` | NO | `sync` | `get_train_why_late` | `api\live_routes.py:201` |

## 0.2 Database Schema Inventory (`data/railtwin.db`)
- **Total DB Tables:** 60
- **Code-Referenced Write Tables:** 52
- **Tables Written by Code but Absent from DB:** 3
  - Flagged: `feature_snapshots_v3, route_cum_km, sqlite`
- **Tables in DB with No Direct Python INSERT/UPDATE/DELETE:** 11
  - Static/Lookup/External tables: `hist_baselines, live_ingest_events, rake_links, route_stations, schema_migrations, section_advisories, sections, shadow_log, staff, weather, weather_hourly`

### Database Tables Detail
| Table Name | Row Count | Primary Key | Column Count | Indexes | Code Writers |
|---|---|---|---|---|---|
| `access_requests` | 0 | `request_id` | 9 | 2 idx | 2 files |
| `ad_events` | 8 | `id` | 13 | 2 idx | 1 files |
| `advisory_ack_log` | 85 | `id` | 6 | 1 idx | 2 files |
| `audit_log` | 55 | `id` | 11 | 3 idx | 1 files |
| `auth_sessions` | 11 | `token_id` | 8 | 4 idx | 1 files |
| `backups` | 36 | `id` | 7 | 0 idx | 1 files |
| `block_status` | 1 | `block_id` | 9 | 2 idx | 2 files |
| `brain_advisory_audit` | 47 | `id` | 11 | 1 idx | 1 files |
| `breathalyzer_tests` | 8 | `id` | 11 | 1 idx | 1 files |
| `cleaning_logs` | 7 | `id` | 9 | 1 idx | 1 files |
| `commercial_stalls` | 1 | `id` | 12 | 2 idx | 1 files |
| `conformal_pid_state` | 0 | `group_key` | 7 | 1 idx | 1 files |
| `corridor_sections` | 4 | `section_id` | 7 | 2 idx | 1 files |
| `crew_rosters` | 8 | `id` | 13 | 1 idx | 1 files |
| `cross_station_locks` | 4 | `id` | 11 | 1 idx | 1 files |
| `delay_certificates` | 7 | `id` | 14 | 4 idx | 1 files |
| `eta_prediction_ledger` | 2,109 | `id` | 15 | 3 idx | 2 files |
| `handover_log` | 5 | `id` | 14 | 1 idx | 1 files |
| `hist_baselines` | 1,200 | `train_no,station_code` | 7 | 2 idx | None (Static/Migration-only) |
| `incidents` | 4 | `id` | 11 | 1 idx | 1 files |
| `level_crossings` | 4 | `id` | 10 | 2 idx | 1 files |
| `live_delay_ledger` | 196 | `id` | 13 | 2 idx | 1 files |
| `live_ingest_events` | 0 | `id` | 7 | 1 idx | None (Static/Migration-only) |
| `live_positions` | 611 | `train_no,run_date` | 16 | 3 idx | 1 files |
| `lost_and_found` | 7 | `id` | 14 | 1 idx | 1 files |
| `notification_ack` | 4 | `id` | 6 | 1 idx | 1 files |
| `notification_log` | 40 | `id` | 9 | 2 idx | 2 files |
| `notifications` | 91 | `id` | 13 | 3 idx | 2 files |
| `planner_changesets` | 4 | `id` | 8 | 1 idx | 1 files |
| `platform_assignments` | 12 | `id` | 11 | 1 idx | 2 files |
| `platform_states` | 2 | `station_code,platform` | 7 | 1 idx | 3 files |
| `possessions` | 4 | `id` | 16 | 1 idx | 1 files |
| `rake_links` | 14 | `incoming_train,outgoing_train` | 4 | 1 idx | None (Static/Migration-only) |
| `rakes` | 4 | `id` | 12 | 3 idx | 1 files |
| `roles` | 9 | `id` | 4 | 1 idx | 1 files |
| `route_stations` | 1,205 | `train_no,seq` | 7 | 1 idx | None (Static/Migration-only) |
| `run_snapshots` | 15 | `snapshot_id` | 14 | 2 idx | 1 files |
| `sahayak_roster` | 5 | `id` | 10 | 2 idx | 1 files |
| `schema_migrations` | 14 | `version` | 3 | 0 idx | None (Static/Migration-only) |
| `section_advisories` | 0 | `id` | 12 | 1 idx | None (Static/Migration-only) |
| `sections` | 14 | `from_code,to_code` | 7 | 1 idx | None (Static/Migration-only) |
| `shadow_log` | 0 | `id` | 10 | 0 idx | None (Static/Migration-only) |
| `shunting_moves` | 4 | `id` | 13 | 1 idx | 1 files |
| `sim_ledger` | 2,399 | `ROWID` | 8 | 1 idx | 1 files |
| `sop_runs` | 4 | `id` | 10 | 1 idx | 1 files |
| `speed_restrictions` | 9 | `id` | 14 | 1 idx | 1 files |
| `staff` | 10 | `staff_id` | 7 | 2 idx | None (Static/Migration-only) |
| `staff_shifts` | 4 | `id` | 9 | 1 idx | 1 files |
| `station_assets` | 6 | `id` | 9 | 2 idx | 1 files |
| `station_events` | 33,601 | `train_no,run_date,seq` | 13 | 6 idx | 1 files |
| `stations` | 112 | `code` | 8 | 1 idx | 1 files |
| `timetable_entries` | 4 | `id` | 15 | 2 idx | 1 files |
| `timetable_versions` | 4 | `id` | 9 | 1 idx | 1 files |
| `train_runs` | 5 | `run_id` | 7 | 2 idx | 1 files |
| `trains` | 151 | `train_no` | 6 | 1 idx | 1 files |
| `user_roles` | 10 | `user_id,role_id` | 2 | 1 idx | 1 files |
| `users` | 10 | `id` | 9 | 6 idx | 3 files |
| `weather` | 3,080 | `date,station_code` | 12 | 1 idx | None (Static/Migration-only) |
| `weather_hourly` | 1 | `station_code,ts_ist` | 10 | 3 idx | None (Static/Migration-only) |
| `work_orders` | 4 | `id` | 11 | 1 idx | 1 files |

## 0.3 ML Artifact Inventory (`ml/artifacts/`)
- **Total Artifact Files:** 18

| Artifact Filename | Size (KB) | Key Code Loaders | Boot Criticality & Missing-File Fallback |
|---|---|---|---|
| `artifact_integrity.json` | 0.8 KB | `api\routes.py`, `ml\artifact_integrity.py` | Diagnostic/Proof |
| `candidate0_manifest.json` | 3.1 KB | None (Orphan/Archive) | Critical (Serving Champion) |
| `candidate0_metrics.json` | 7.1 KB | `scripts\candidate_shootout.py`, `scripts\read_c0.py` | Diagnostic/Proof |
| `drift_report.json` | 1.7 KB | `api\routes.py`, `ml\drift.py`, `scripts\nightly_pipeline.py` | Diagnostic/Proof |
| `gru_config.json` | 0.4 KB | `ml\audit.py`, `ml\model_seq.py` | Diagnostic/Proof |
| `manifest.json` | 2.6 KB | `api\predictor.py`, `api\routes.py`, `api\system_routes.py` | Critical (Serving Champion) |
| `metrics.json` | 9.6 KB | `api\routes.py`, `ml\evaluate.py`, `scripts\candidate_shootout.py` | Diagnostic/Proof |
| `model_delta_q10.txt` | 4109.5 KB | `ml\artifact_integrity.py` | Critical (Serving Champion) |
| `model_delta_q50.txt` | 4080.9 KB | `ml\artifact_integrity.py` | Critical (Serving Champion) |
| `model_delta_q90.txt` | 4066.1 KB | `ml\artifact_integrity.py` | Critical (Serving Champion) |
| `model_direct_q10.txt` | 4094.1 KB | `api\routes.py`, `ml\artifact_integrity.py`, `scripts\closing_c245.py` | Critical (Serving Champion) |
| `model_direct_q50.txt` | 4070.1 KB | `api\predictor.py`, `api\routes.py`, `api\system_routes.py` | Critical (Serving Champion) |
| `model_direct_q90.txt` | 4078.9 KB | `api\routes.py`, `ml\artifact_integrity.py`, `scripts\closing_c245.py` | Critical (Serving Champion) |
| `model_gru_challenger.pt` | 915.4 KB | `api\predictor.py`, `api\system_routes.py`, `ml\artifact_integrity.py` | Critical (Serving Champion) |
| `model_lr_benchmark.pkl` | 1.7 KB | `ml\artifact_integrity.py`, `ml\ensemble.py`, `ml\evaluate.py` | Critical (Serving Champion) |
| `perf_bench.json` | 0.4 KB | `scripts\perf_bench.py` | Diagnostic/Proof |
| `registry.json` | 0.9 KB | `api\predictor.py`, `ml\audit.py`, `ml\ensemble.py` | Critical (Serving Champion) |
| `shootout_results.json` | 3.4 KB | `scripts\candidate_shootout.py` | Diagnostic/Proof |

## 0.4 Startup Trace & Import-Time Side-Effects

### Boot Order in `api/main.py`:
1. **Module Import Phase:**
   - Evaluates imports across 22 router modules.
   - **Side-Effect Check:** `config.settings` parses `.env`.
   - `data.db.Database` class is imported; `get_db()` singleton is NOT evaluated at import time.
   - `PredictorService` is LAZY: `_DEFAULT_PREDICTOR = None` instantiated only upon first call to `get_predictor_service()`.
   - `engine.live_tracker` module is loaded; singleton created at boot.
2. **Lifespan Startup (`lifespan(app)`):**
   - Step 1: `torch.set_num_threads(1)` (caps thread thrashing under concurrent workers).
   - Step 2: `db = get_db()` -> connects to SQLite `data/railtwin.db`.
   - Step 3: `db.init_schema()` -> applies table definitions if missing.
   - Step 4: `db.materialize_historical_baselines()` -> queries `station_events` and populates `historical_baselines`.
   - Step 5: `tracker = get_live_tracker(db); await tracker.start()` -> launches background `asyncio.create_task` for live position extrapolation.
3. **Middleware Initialization:**
   - `RequestContextMiddleware` (X-Request-ID correlation).
   - `SecurityHeaders` (nosniff, DENY, CSP).
   - `GZipMiddleware` (compression).
   - `CORSMiddleware` (`allow_origins=["*"]`).
   - `IdempotencyMiddleware` (mutation idempotency via headers).
   - `ResponseCacheMiddleware` (5-second TTL cache for `/v1/advise`).
   - `TokenBucketRateLimiter` (60 req/min per IP, 10-token burst).
4. **Shutdown Phase (`lifespan` exit):**
   - `await tracker.stop()` -> cancels live tracker background task cleanly.


## 0.5 Background Processes & Concurrency Hazards
- **Identified Background Tasks / Schedulers:** 1

| Location | Type | Code Line | Lifecycle / Hazard Analysis |
|---|---|---|---|
| `engine\live_tracker.py:191` | `asyncio_task` | `self._task = asyncio.create_task(self._run_loop())` | Managed |

## 0.6 Frontend Contract List (`web/src`)
- **Identified API Calls in Frontend:** 38

| Frontend File:Line | Method | URL / Path | TypeScript Return Type |
|---|---|---|---|
| `web\src\lib\api.ts:317` | `FETCH` | `${API_BASE}${path}` | `raw` |
| `web\src\lib\api.ts:364` | `GET` | `/v1/network/state` | `any` |
| `web\src\lib\api.ts:374` | `GET` | `/v1/network/state` | `any` |
| `web\src\lib\api.ts:432` | `GET` | `/v1/trains/${number}/journey` | `any` |
| `web\src\lib\api.ts:562` | `GET` | `/v1/trains/${trainNo}/live` | `any` |
| `web\src\lib\api.ts:566` | `GET` | `/v1/pnr/${pnrNo}` | `any` |
| `web\src\lib\api.ts:610` | `GET` | `/api/platform/states` | `any` |
| `web\src\lib\api.ts:614` | `POST` | `/api/platform/reoptimize` | `any` |
| `web\src\lib\api.ts:620` | `POST` | `/api/platform/rollback` | `any` |
| `web\src\lib\api.ts:629` | `GET` | `/v1/crew/alerts` | `any` |
| `web\src\lib\api.ts:630` | `GET` | `/api/section/advisories/generate` | `any[]` |
| `web\src\lib\api.ts:732` | `GET` | `/api/workforce/crew/roster` | `any` |
| `web\src\lib\api.ts:743` | `POST` | `/api/workforce/crew/signon` | `any` |
| `web\src\lib\api.ts:750` | `GET` | `/api/safety/possessions` | `any` |
| `web\src\lib\api.ts:755` | `GET` | `/api/audit/logs` | `any` |
| `web\src\lib\api.ts:759` | `GET` | `/api/audit/verify-integrity` | `any` |
| `web\src\lib\api.ts:769` | `GET` | `/v1/evaluation/summary` | `any` |
| `web\src\lib\api.ts:774` | `GET` | `/api/timetable/versions` | `any` |
| `web\src\lib\api.ts:782` | `GET` | `/api/timetable/versions/${versionId}/entries` | `any` |
| `web\src\lib\api.ts:800` | `POST` | `/api/timetable/versions/${versionId}/publish` | `any` |
| `web\src\lib\api.ts:809` | `GET` | `/api/blocks/status` | `any` |
| `web\src\lib\api.ts:821` | `GET` | `/api/safety/tsr` | `any` |
| `web\src\lib\api.ts:829` | `POST` | `/api/safety/tsr` | `any` |
| `web\src\lib\api.ts:837` | `POST` | `/api/safety/tsr/${id}/lift` | `any` |
| `web\src\lib\api.ts:846` | `GET` | `/api/safety/incidents` | `any` |
| `web\src\lib\api.ts:854` | `POST` | `/api/safety/incidents` | `any` |
| `web\src\lib\api.ts:863` | `GET` | `/api/section/handoffs` | `any` |
| `web\src\lib\api.ts:872` | `POST` | `/api/section/handoffs/${id}/ack` | `any` |
| `web\src\lib\api.ts:881` | `GET` | `/api/section/dfc` | `any` |
| `web\src\lib\api.ts:896` | `GET` | `/v1/model/performance` | `ModelPerformanceData` |
| `web\src\lib\api.ts:907` | `GET` | `/v1/demo/inject-event` | `any` |
| `web\src\lib\api.ts:914` | `GET` | `/v1/demo/reset-events` | `any` |
| `web\src\lib\useLiveMotionEngine.ts:202` | `SSE` | `streamUrl` | `EventSource` |
| `web\src\mock\auth.ts:196` | `FETCH` | `${API_BASE}/api/auth/login` | `raw` |
| `web\src\mock\auth.ts:267` | `FETCH` | `${API_BASE}/api/auth/refresh` | `raw` |
| `web\src\mock\auth.ts:353` | `FETCH` | `${API_BASE}/api/auth/logout` | `raw` |
| `web\src\pages\dashboard\LiveMapPage.tsx:82` | `FETCH` | `${API_BASE}/v1/live/positions` | `raw` |
| `web\src\pages\landing\LandingPage.tsx:64` | `FETCH` | `${API_BASE}/api/access-requests` | `raw` |