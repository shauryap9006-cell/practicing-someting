# RailTwin-X System Map (Phase 0 Audit Deliverable)

> Generated via dynamic introspection and static AST cross-referencing.
> Environment: Windows / PowerShell / Python 3.14 / SQLite / FastAPI.

---

## 0.1 ROUTE INVENTORY

Total Mounted Routes: **212**
All 22 router modules in `api/` are included in `api/main.py`. Unmounted router files: **0**.

| HTTP Method(s) | Full Path | Auth Required | Handler Function | Async? | Source Location |
|---|---|---|---|---|---|
| `GET` | `/` | NO | `root_redirect` | sync (def) | `main.py:266` |
| `POST` | `/api/access-requests` | NO | `create_access_request` | sync (def) | `access_routes.py:30` |
| `GET` | `/api/admin/access-requests` | NO | `list_access_requests` | sync (def) | `admin_routes.py:81` |
| `PUT` | `/api/admin/access-requests/{request_id}` | NO | `review_access_request` | sync (def) | `admin_routes.py:102` |
| `GET` | `/api/admin/backups` | NO | `list_backups` | sync (def) | `admin_routes.py:348` |
| `POST` | `/api/admin/backups/create` | NO | `trigger_backup` | sync (def) | `admin_routes.py:382` |
| `POST` | `/api/admin/backups/verify` | NO | `verify_latest_backup` | sync (def) | `admin_routes.py:401` |
| `GET` | `/api/admin/users` | NO | `list_users` | sync (def) | `admin_routes.py:138` |
| `POST` | `/api/admin/users` | NO | `create_user` | sync (def) | `admin_routes.py:176` |
| `PUT` | `/api/admin/users/{user_id}` | NO | `update_user` | sync (def) | `admin_routes.py:254` |
| `GET` | `/api/audit/logs` | NO | `get_audit_logs` | sync (def) | `audit_routes.py:48` |
| `GET` | `/api/audit/verify-integrity` | NO | `verify_audit_trail_integrity` | sync (def) | `audit_routes.py:106` |
| `POST` | `/api/auth/login` | NO | `login` | sync (def) | `auth_routes.py:54` |
| `POST` | `/api/auth/logout` | NO | `logout` | sync (def) | `auth_routes.py:228` |
| `GET` | `/api/auth/me` | NO | `get_current_user_profile` | sync (def) | `auth_routes.py:141` |
| `POST` | `/api/auth/refresh` | NO | `refresh_token` | sync (def) | `auth_routes.py:156` |
| `GET` | `/api/blocks/status` | NO | `get_block_statuses` | sync (def) | `block_routes.py:34` |
| `POST` | `/api/blocks/{block_id}/line-clear` | NO | `grant_line_clear` | sync (def) | `block_routes.py:145` |
| `POST` | `/api/blocks/{block_id}/state` | NO | `update_block_state` | sync (def) | `block_routes.py:104` |
| `GET` | `/api/board/kiosk` | NO | `get_kiosk_board` | sync (def) | `board_routes.py:209` |
| `GET` | `/api/board/live` | NO | `get_live_board` | sync (def) | `board_routes.py:39` |
| `GET` | `/api/board/stream` | NO | `stream_live_board` | async | `board_routes.py:257` |
| `GET` | `/api/commercial/announcements/generate` | NO | `generate_platform_announcement` | sync (def) | `commercial_routes.py:179` |
| `POST` | `/api/commercial/delay-certificate` | NO | `issue_delay_certificate` | sync (def) | `commercial_routes.py:39` |
| `GET` | `/api/commercial/delay-certificate/verify/{qr_token}` | NO | `verify_delay_certificate` | sync (def) | `commercial_routes.py:148` |
| `GET` | `/api/commercial/delay-certificate/{cert_no}` | NO | `get_delay_certificate` | sync (def) | `commercial_routes.py:132` |
| `GET` | `/api/commercial/lost-found` | NO | `list_lost_items` | sync (def) | `commercial_routes.py:426` |
| `POST` | `/api/commercial/lost-found` | NO | `register_lost_item` | sync (def) | `commercial_routes.py:382` |
| `PUT` | `/api/commercial/lost-found/{item_id}/claim` | NO | `claim_lost_item` | sync (def) | `commercial_routes.py:453` |
| `GET` | `/api/commercial/stalls` | NO | `list_commercial_stalls` | sync (def) | `commercial_routes.py:314` |
| `POST` | `/api/commercial/stalls` | NO | `register_commercial_stall` | sync (def) | `commercial_routes.py:264` |
| `GET` | `/api/coordination/advisories/generate` | NO | `generate_precedence_advisories` | sync (def) | `section_routes.py:239` |
| `POST` | `/api/coordination/advisories/{adv_id}/execute` | NO | `execute_precedence_advisory` | sync (def) | `section_routes.py:283` |
| `GET` | `/api/coordination/corridor` | NO | `get_corridor_topology` | sync (def) | `section_routes.py:37` |
| `GET` | `/api/coordination/dfc` | NO | `get_dfc_precedence` | sync (def) | `section_routes.py:315` |
| `POST` | `/api/coordination/handoff/request` | NO | `request_cross_station_handoff` | sync (def) | `section_routes.py:80` |
| `PUT` | `/api/coordination/handoff/{lock_id}/grant` | NO | `grant_cross_station_handoff` | sync (def) | `section_routes.py:131` |
| `PUT` | `/api/coordination/handoff/{lock_id}/release` | NO | `release_cross_station_handoff` | sync (def) | `section_routes.py:169` |
| `GET` | `/api/coordination/handoffs` | NO | `list_cross_station_handoffs` | sync (def) | `section_routes.py:206` |
| `GET` | `/api/coordination/precedence` | NO | `generate_precedence_advisories` | sync (def) | `section_routes.py:239` |
| `GET` | `/api/handover/current` | NO | `get_current_handover_summary` | sync (def) | `handover_routes.py:138` |
| `POST` | `/api/handover/draft` | NO | `create_or_update_draft` | sync (def) | `handover_routes.py:165` |
| `GET` | `/api/handover/history` | NO | `list_handover_history` | sync (def) | `handover_routes.py:370` |
| `POST` | `/api/handover/{handover_id}/ack-in` | NO | `acknowledge_incoming_shift` | sync (def) | `handover_routes.py:310` |
| `POST` | `/api/handover/{handover_id}/sign-out` | NO | `sign_out_shift` | sync (def) | `handover_routes.py:257` |
| `GET` | `/api/infra/assets` | NO | `list_station_assets` | sync (def) | `infra_routes.py:197` |
| `POST` | `/api/infra/assets` | NO | `register_station_asset` | sync (def) | `infra_routes.py:151` |
| `GET` | `/api/infra/cleaning-logs` | NO | `list_cleaning_logs` | sync (def) | `infra_routes.py:441` |
| `POST` | `/api/infra/cleaning-logs` | NO | `record_cleaning_log` | sync (def) | `infra_routes.py:407` |
| `GET` | `/api/infra/feedback` | NO | `list_cleaning_logs` | sync (def) | `infra_routes.py:441` |
| `GET` | `/api/infra/rakes` | NO | `list_rakes` | sync (def) | `infra_routes.py:91` |
| `POST` | `/api/infra/rakes` | NO | `register_rake_bpc` | sync (def) | `infra_routes.py:41` |
| `GET` | `/api/infra/work-orders` | NO | `list_work_orders` | sync (def) | `infra_routes.py:319` |
| `POST` | `/api/infra/work-orders` | NO | `create_work_order` | sync (def) | `infra_routes.py:259` |
| `PUT` | `/api/infra/work-orders/{wo_id}/resolve` | NO | `resolve_work_order` | sync (def) | `infra_routes.py:350` |
| `GET` | `/api/infrastructure/assets` | NO | `list_station_assets` | sync (def) | `infra_routes.py:197` |
| `POST` | `/api/infrastructure/assets` | NO | `register_station_asset` | sync (def) | `infra_routes.py:151` |
| `GET` | `/api/infrastructure/cleaning-logs` | NO | `list_cleaning_logs` | sync (def) | `infra_routes.py:441` |
| `POST` | `/api/infrastructure/cleaning-logs` | NO | `record_cleaning_log` | sync (def) | `infra_routes.py:407` |
| `GET` | `/api/infrastructure/feedback` | NO | `list_cleaning_logs` | sync (def) | `infra_routes.py:441` |
| `GET` | `/api/infrastructure/rakes` | NO | `list_rakes` | sync (def) | `infra_routes.py:91` |
| `POST` | `/api/infrastructure/rakes` | NO | `register_rake_bpc` | sync (def) | `infra_routes.py:41` |
| `GET` | `/api/infrastructure/work-orders` | NO | `list_work_orders` | sync (def) | `infra_routes.py:319` |
| `POST` | `/api/infrastructure/work-orders` | NO | `create_work_order` | sync (def) | `infra_routes.py:259` |
| `PUT` | `/api/infrastructure/work-orders/{wo_id}/resolve` | NO | `resolve_work_order` | sync (def) | `infra_routes.py:350` |
| `GET` | `/api/notifications/active` | NO | `get_active_notifications` | sync (def) | `notification_routes.py:58` |
| `POST` | `/api/notifications/emit` | NO | `emit_notification_endpoint` | sync (def) | `notification_routes.py:155` |
| `POST` | `/api/notifications/escalate` | NO | `trigger_escalation_ladder` | sync (def) | `notification_routes.py:189` |
| `POST` | `/api/notifications/{notification_id}/ack` | NO | `ack_notification_endpoint` | sync (def) | `notification_routes.py:113` |
| `GET` | `/api/ops/ad-events` | NO | `list_ad_events` | sync (def) | `ops_routes.py:240` |
| `POST` | `/api/ops/setin/{train_no}` | NO | `record_set_in` | sync (def) | `ops_routes.py:55` |
| `POST` | `/api/ops/setout/{train_no}` | NO | `record_set_out` | sync (def) | `ops_routes.py:157` |
| `GET` | `/api/ops/shunting` | NO | `list_shunting_moves` | sync (def) | `ops_routes.py:356` |
| `POST` | `/api/ops/shunting` | NO | `create_shunting_move` | sync (def) | `ops_routes.py:287` |
| `PUT` | `/api/ops/shunting/{move_id}/status` | NO | `update_shunting_status` | sync (def) | `ops_routes.py:403` |
| `POST` | `/api/planner/apply` | NO | `apply_day_changeset` | sync (def) | `planner_routes.py:100` |
| `GET` | `/api/planner/changesets` | NO | `list_planner_changesets` | sync (def) | `planner_routes.py:176` |
| `POST` | `/api/planner/simulate` | NO | `simulate_day_changeset` | sync (def) | `planner_routes.py:41` |
| `POST` | `/api/platform/assign` | NO | `assign_platform` | sync (def) | `platform_routes.py:148` |
| `POST` | `/api/platform/assignments/{assign_id}/lock` | NO | `toggle_assignment_lock` | sync (def) | `platform_routes.py:243` |
| `POST` | `/api/platform/block` | NO | `set_platform_block` | sync (def) | `platform_routes.py:90` |
| `POST` | `/api/platform/reoptimize` | NO | `reoptimize_station_platforms` | sync (def) | `platform_routes.py:285` |
| `GET` | `/api/platform/states` | NO | `get_platform_states` | sync (def) | `platform_routes.py:45` |
| `GET` | `/api/safety/incidents` | NO | `list_incidents` | sync (def) | `safety_routes.py:476` |
| `POST` | `/api/safety/incidents` | NO | `report_incident` | sync (def) | `safety_routes.py:419` |
| `GET` | `/api/safety/lc/status` | NO | `list_level_crossings` | sync (def) | `safety_routes.py:708` |
| `PUT` | `/api/safety/lc/{lc_id}/status` | NO | `update_lc_status` | sync (def) | `safety_routes.py:753` |
| `POST` | `/api/safety/possession/request` | NO | `request_possession` | sync (def) | `safety_routes.py:187` |
| `POST` | `/api/safety/possession/{possession_id}/grant` | NO | `grant_possession` | sync (def) | `safety_routes.py:233` |
| `POST` | `/api/safety/possession/{possession_id}/restore` | NO | `restore_possession` | sync (def) | `safety_routes.py:314` |
| `GET` | `/api/safety/possessions` | NO | `list_possessions` | sync (def) | `safety_routes.py:379` |
| `GET` | `/api/safety/sop/active` | NO | `list_active_sop_runs` | sync (def) | `safety_routes.py:675` |
| `POST` | `/api/safety/sop/start` | NO | `start_sop_run` | sync (def) | `safety_routes.py:556` |
| `GET` | `/api/safety/sop/templates` | NO | `get_sop_templates` | sync (def) | `safety_routes.py:545` |
| `POST` | `/api/safety/sop/{run_id}/step` | NO | `complete_sop_step` | sync (def) | `safety_routes.py:617` |
| `GET` | `/api/safety/tsr` | NO | `list_speed_restrictions` | sync (def) | `safety_routes.py:115` |
| `POST` | `/api/safety/tsr` | NO | `create_speed_restriction` | sync (def) | `safety_routes.py:43` |
| `DELETE` | `/api/safety/tsr/{tsr_id}` | NO | `cancel_speed_restriction` | sync (def) | `safety_routes.py:142` |
| `GET` | `/api/section/advisories/generate` | NO | `generate_precedence_advisories` | sync (def) | `section_routes.py:239` |
| `POST` | `/api/section/advisories/{adv_id}/execute` | NO | `execute_precedence_advisory` | sync (def) | `section_routes.py:283` |
| `GET` | `/api/section/corridor` | NO | `get_corridor_topology` | sync (def) | `section_routes.py:37` |
| `GET` | `/api/section/dfc` | NO | `get_dfc_precedence` | sync (def) | `section_routes.py:315` |
| `POST` | `/api/section/handoff/request` | NO | `request_cross_station_handoff` | sync (def) | `section_routes.py:80` |
| `PUT` | `/api/section/handoff/{lock_id}/grant` | NO | `grant_cross_station_handoff` | sync (def) | `section_routes.py:131` |
| `PUT` | `/api/section/handoff/{lock_id}/release` | NO | `release_cross_station_handoff` | sync (def) | `section_routes.py:169` |
| `GET` | `/api/section/handoffs` | NO | `list_cross_station_handoffs` | sync (def) | `section_routes.py:206` |
| `GET` | `/api/section/precedence` | NO | `generate_precedence_advisories` | sync (def) | `section_routes.py:239` |
| `GET` | `/api/system/model-info` | NO | `get_system_model_info` | sync (def) | `system_routes.py:89` |
| `GET` | `/api/system/status` | NO | `get_system_status` | sync (def) | `system_routes.py:20` |
| `POST` | `/api/timetable/entries` | NO | `create_timetable_entry` | sync (def) | `timetable_routes.py:209` |
| `DELETE` | `/api/timetable/entries/{entry_id}` | NO | `delete_timetable_entry` | sync (def) | `timetable_routes.py:323` |
| `PUT` | `/api/timetable/entries/{entry_id}` | NO | `update_timetable_entry` | sync (def) | `timetable_routes.py:264` |
| `GET` | `/api/timetable/versions` | NO | `list_timetable_versions` | sync (def) | `timetable_routes.py:59` |
| `POST` | `/api/timetable/versions` | NO | `create_timetable_version` | sync (def) | `timetable_routes.py:99` |
| `GET` | `/api/timetable/versions/{version_id}/entries` | NO | `get_version_entries` | sync (def) | `timetable_routes.py:150` |
| `POST` | `/api/timetable/versions/{version_id}/import-seed` | NO | `import_seed_timetable` | sync (def) | `timetable_routes.py:394` |
| `POST` | `/api/timetable/versions/{version_id}/publish` | NO | `publish_timetable_version` | sync (def) | `timetable_routes.py:450` |
| `GET` | `/api/timetable/versions/{version_id}/validate` | NO | `validate_timetable_version` | sync (def) | `timetable_routes.py:352` |
| `POST` | `/api/v1/advise` | NO | `post_brain_advise` | sync (def) | `routes.py:972` |
| `POST` | `/api/v1/advise/{adv_id}/ack` | NO | `post_advisory_ack` | sync (def) | `routes.py:1074` |
| `GET` | `/api/v1/cascade/ripple` | NO | `get_cascade_ripple` | sync (def) | `demo_routes.py:340` |
| `GET` | `/api/v1/conflicts/{train_no}` | NO | `get_train_conflicts` | sync (def) | `routes.py:990` |
| `GET` | `/api/v1/corridor/congestion-radar` | NO | `get_corridor_congestion_radar` | sync (def) | `demo_routes.py:646` |
| `GET` | `/api/v1/crew/alerts` | NO | `get_crew_alerts` | sync (def) | `routes.py:828` |
| `GET` | `/api/v1/demo/comparator` | NO | `get_demo_comparator` | sync (def) | `demo_routes.py:89` |
| `POST` | `/api/v1/demo/inject-event` | NO | `inject_shock_event` | sync (def) | `demo_routes.py:54` |
| `POST` | `/api/v1/demo/reset-events` | NO | `reset_shock_events` | sync (def) | `demo_routes.py:76` |
| `GET` | `/api/v1/demo/shocks` | NO | `get_active_shocks` | sync (def) | `demo_routes.py:43` |
| `GET` | `/api/v1/demo/time-machine` | NO | `get_demo_time_machine` | sync (def) | `demo_routes.py:457` |
| `GET` | `/api/v1/evaluation/summary` | NO | `get_evaluation_summary` | sync (def) | `routes.py:45` |
| `GET` | `/api/v1/health` | NO | `get_health` | sync (def) | `routes.py:1214` |
| `POST` | `/api/v1/hooks/whatsapp` | NO | `whatsapp_inbound_webhook` | async | `routes.py:1116` |
| `GET` | `/api/v1/ledger/scoreboard` | NO | `get_prediction_ledger_scoreboard` | sync (def) | `routes.py:881` |
| `GET` | `/api/v1/ledger/verify` | NO | `verify_prediction_ledger_chain` | sync (def) | `routes.py:893` |
| `GET` | `/api/v1/live/positions` | NO | `get_live_positions` | sync (def) | `live_routes.py:256` |
| `GET` | `/api/v1/live/stream` | NO | `stream_live_positions` | async | `live_routes.py:275` |
| `GET` | `/api/v1/meta/config` | NO | `get_meta_config` | sync (def) | `live_routes.py:46` |
| `GET` | `/api/v1/meta/models` | NO | `get_models_meta` | sync (def) | `routes.py:911` |
| `GET` | `/api/v1/meta/stations` | NO | `get_meta_stations` | sync (def) | `routes.py:936` |
| `GET` | `/api/v1/meta/trains` | NO | `get_meta_trains` | sync (def) | `routes.py:954` |
| `GET` | `/api/v1/model/performance` | NO | `get_model_performance` | sync (def) | `routes.py:66` |
| `GET` | `/api/v1/network/state` | NO | `get_network_state` | sync (def) | `routes.py:501` |
| `GET` | `/api/v1/passenger/pnr/{pnr}` | NO | `get_pnr` | sync (def) | `passenger_routes.py:490` |
| `GET` | `/api/v1/passenger/popular` | NO | `get_popular_trains` | sync (def) | `passenger_routes.py:369` |
| `GET` | `/api/v1/passenger/search` | NO | `search_trains` | sync (def) | `passenger_routes.py:280` |
| `GET` | `/api/v1/passenger/search` | NO | `passenger_search` | sync (def) | `routes.py:457` |
| `GET` | `/api/v1/passenger/snapshot` | NO | `get_passenger_snapshot` | sync (def) | `passenger_routes.py:506` |
| `GET` | `/api/v1/passenger/stream` | NO | `stream_passenger_train` | async | `passenger_routes.py:155` |
| `GET` | `/api/v1/pnr/{pnr_no}` | NO | `get_pnr_status` | sync (def) | `routes.py:321` |
| `POST` | `/api/v1/simulate/what-if` | NO | `simulate_what_if` | sync (def) | `routes.py:771` |
| `GET` | `/api/v1/stations/{code}` | NO | `get_station_summary` | sync (def) | `routes.py:650` |
| `GET` | `/api/v1/stations/{code}/connections` | NO | `get_station_connections` | sync (def) | `routes.py:847` |
| `GET` | `/api/v1/stations/{code}/gantt` | NO | `get_station_gantt` | sync (def) | `routes.py:708` |
| `POST` | `/api/v1/stations/{code}/reoptimize` | NO | `reoptimize_station_platforms` | sync (def) | `routes.py:739` |
| `GET` | `/api/v1/trains/{train_no}/autopsy` | NO | `get_train_autopsy` | sync (def) | `routes.py:283` |
| `GET` | `/api/v1/trains/{train_no}/eta` | NO | `get_train_eta` | sync (def) | `routes.py:146` |
| `GET` | `/api/v1/trains/{train_no}/journey` | NO | `get_train_journey` | sync (def) | `routes.py:172` |
| `GET` | `/api/v1/trains/{train_no}/live` | NO | `get_train_live` | sync (def) | `live_routes.py:96` |
| `GET` | `/api/v1/trains/{train_no}/why-late` | NO | `get_train_why_late` | sync (def) | `live_routes.py:201` |
| `GET` | `/api/workforce/breathalyzer` | NO | `list_breathalyzer_tests` | sync (def) | `workforce_routes.py:111` |
| `POST` | `/api/workforce/breathalyzer` | NO | `record_breathalyzer_test` | sync (def) | `workforce_routes.py:39` |
| `GET` | `/api/workforce/crew/breaches` | NO | `check_crew_breaches` | sync (def) | `workforce_routes.py:320` |
| `GET` | `/api/workforce/crew/roster` | NO | `list_crew_roster` | sync (def) | `workforce_routes.py:255` |
| `POST` | `/api/workforce/crew/sign-on` | NO | `crew_sign_on` | sync (def) | `workforce_routes.py:142` |
| `POST` | `/api/workforce/crew/{roster_id}/sign-off` | NO | `crew_sign_off` | sync (def) | `workforce_routes.py:203` |
| `GET` | `/api/workforce/sahayak` | NO | `list_sahayak_roster` | sync (def) | `workforce_routes.py:441` |
| `PUT` | `/api/workforce/sahayak/{sahayak_id}/duty` | NO | `toggle_sahayak_duty` | sync (def) | `workforce_routes.py:491` |
| `GET` | `/api/workforce/shifts` | NO | `list_staff_shifts` | sync (def) | `workforce_routes.py:387` |
| `POST` | `/api/workforce/shifts` | NO | `assign_staff_shift` | sync (def) | `workforce_routes.py:344` |
| `GET` | `/healthz` | NO | `liveness_probe` | sync (def) | `main.py:253` |
| `GET` | `/readyz` | NO | `readiness_probe` | sync (def) | `main.py:259` |
| `POST` | `/v1/advise` | NO | `post_brain_advise` | sync (def) | `routes.py:972` |
| `POST` | `/v1/advise/{adv_id}/ack` | NO | `post_advisory_ack` | sync (def) | `routes.py:1074` |
| `GET` | `/v1/cascade/ripple` | NO | `get_cascade_ripple` | sync (def) | `demo_routes.py:340` |
| `GET` | `/v1/conflicts/{train_no}` | NO | `get_train_conflicts` | sync (def) | `routes.py:990` |
| `GET` | `/v1/corridor/congestion-radar` | NO | `get_corridor_congestion_radar` | sync (def) | `demo_routes.py:646` |
| `GET` | `/v1/crew/alerts` | NO | `get_crew_alerts` | sync (def) | `routes.py:828` |
| `GET` | `/v1/demo/comparator` | NO | `get_demo_comparator` | sync (def) | `demo_routes.py:89` |
| `POST` | `/v1/demo/inject-event` | NO | `inject_shock_event` | sync (def) | `demo_routes.py:54` |
| `POST` | `/v1/demo/reset-events` | NO | `reset_shock_events` | sync (def) | `demo_routes.py:76` |
| `GET` | `/v1/demo/shocks` | NO | `get_active_shocks` | sync (def) | `demo_routes.py:43` |
| `GET` | `/v1/demo/time-machine` | NO | `get_demo_time_machine` | sync (def) | `demo_routes.py:457` |
| `GET` | `/v1/evaluation/summary` | NO | `get_evaluation_summary` | sync (def) | `routes.py:45` |
| `GET` | `/v1/health` | NO | `get_health` | sync (def) | `routes.py:1214` |
| `POST` | `/v1/hooks/whatsapp` | NO | `whatsapp_inbound_webhook` | async | `routes.py:1116` |
| `GET` | `/v1/ledger/scoreboard` | NO | `get_prediction_ledger_scoreboard` | sync (def) | `routes.py:881` |
| `GET` | `/v1/ledger/verify` | NO | `verify_prediction_ledger_chain` | sync (def) | `routes.py:893` |
| `GET` | `/v1/live/positions` | NO | `get_live_positions` | sync (def) | `live_routes.py:256` |
| `GET` | `/v1/live/stream` | NO | `stream_live_positions` | async | `live_routes.py:275` |
| `GET` | `/v1/meta/config` | NO | `get_meta_config` | sync (def) | `live_routes.py:46` |
| `GET` | `/v1/meta/models` | NO | `get_models_meta` | sync (def) | `routes.py:911` |
| `GET` | `/v1/meta/stations` | NO | `get_meta_stations` | sync (def) | `routes.py:936` |
| `GET` | `/v1/meta/trains` | NO | `get_meta_trains` | sync (def) | `routes.py:954` |
| `GET` | `/v1/model/performance` | NO | `get_model_performance` | sync (def) | `routes.py:66` |
| `GET` | `/v1/network/state` | NO | `get_network_state` | sync (def) | `routes.py:501` |
| `GET` | `/v1/passenger/pnr/{pnr}` | NO | `get_pnr` | sync (def) | `passenger_routes.py:490` |
| `GET` | `/v1/passenger/popular` | NO | `get_popular_trains` | sync (def) | `passenger_routes.py:369` |
| `GET` | `/v1/passenger/search` | NO | `search_trains` | sync (def) | `passenger_routes.py:280` |
| `GET` | `/v1/passenger/search` | NO | `passenger_search` | sync (def) | `routes.py:457` |
| `GET` | `/v1/passenger/snapshot` | NO | `get_passenger_snapshot` | sync (def) | `passenger_routes.py:506` |
| `GET` | `/v1/passenger/stream` | NO | `stream_passenger_train` | async | `passenger_routes.py:155` |
| `GET` | `/v1/pnr/{pnr_no}` | NO | `get_pnr_status` | sync (def) | `routes.py:321` |
| `POST` | `/v1/simulate/what-if` | NO | `simulate_what_if` | sync (def) | `routes.py:771` |
| `GET` | `/v1/stations/{code}` | NO | `get_station_summary` | sync (def) | `routes.py:650` |
| `GET` | `/v1/stations/{code}/connections` | NO | `get_station_connections` | sync (def) | `routes.py:847` |
| `GET` | `/v1/stations/{code}/gantt` | NO | `get_station_gantt` | sync (def) | `routes.py:708` |
| `POST` | `/v1/stations/{code}/reoptimize` | NO | `reoptimize_station_platforms` | sync (def) | `routes.py:739` |
| `GET` | `/v1/trains/{train_no}/autopsy` | NO | `get_train_autopsy` | sync (def) | `routes.py:283` |
| `GET` | `/v1/trains/{train_no}/eta` | NO | `get_train_eta` | sync (def) | `routes.py:146` |
| `GET` | `/v1/trains/{train_no}/journey` | NO | `get_train_journey` | sync (def) | `routes.py:172` |
| `GET` | `/v1/trains/{train_no}/live` | NO | `get_train_live` | sync (def) | `live_routes.py:96` |
| `GET` | `/v1/trains/{train_no}/why-late` | NO | `get_train_why_late` | sync (def) | `live_routes.py:201` |

---

## 0.2 DATABASE SCHEMA INVENTORY (data/railtwin.db)

Total tables in active database: **60**
Total tables written across codebase: **58**

### Critical Schema Anomalies
1. **Table Absent from DB but Referenced in Feature Pipeline:** `route_cum_km`
   - Referenced in `ml/features_v3.py:234` (`SELECT train_no, station_code, seq, cum_km FROM route_cum_km`).
   - Because the table does not exist in `data/railtwin.db`, the query raises `OperationalError` which is swallowed by `except Exception: pass`, silently aborting the fallback query and leaving `cum_km_map`, `train_routes`, and `route_seq_map` empty.
2. **Tables Present in DB with Zero Writes in Code:**
   - `conformal_pid_state` (0 rows in DB, 0 write call sites across `api/`, `engine/`, `collector/`, `safety/`, `scripts/`)
   - `live_ingest_events` (0 rows in DB, 0 write call sites across `api/`, `engine/`, `collector/`, `safety/`, `scripts/`)
   - `section_advisories` (0 rows in DB, 0 write call sites across `api/`, `engine/`, `collector/`, `safety/`, `scripts/`)
   - `shadow_log` (0 rows in DB, 0 write call sites across `api/`, `engine/`, `collector/`, `safety/`, `scripts/`)

### Table Inventory Table
| Table Name | Row Count | Column Count | Indexes | Writing Modules / Code Paths |
|---|---|---|---|---|
| `access_requests` | 0 | 9 | idx_access_requests_status_time | 1 write site(s): api\access_routes.py:40 |
| `ad_events` | 12 | 13 | idx_ad_events_stn_ts, idx_ad_events_run | 2 write site(s): api\ops_routes.py:87, api\ops_routes.py:176 |
| `advisory_ack_log` | 103 | 6 | idx_ack_log_adv | 2 write site(s): api\routes.py:1041, scripts\demo_replay.py:211 |
| `audit_log` | 55 | 11 | idx_audit_log_actor, idx_audit_log_ts, idx_audit_log_table | 1 write site(s): data\audit.py:83 |
| `auth_sessions` | 15 | 8 | idx_auth_sessions_expiry, idx_auth_sessions_user | 4 write site(s): api\auth_routes.py:104, api\auth_routes.py:198 (+2 more) |
| `backups` | 42 | 7 | None (PK only) | 1 write site(s): scripts\backup_db.py:74 |
| `block_status` | 1 | 9 | idx_block_status_section | 3 write site(s): api\block_routes.py:121, api\block_routes.py:167 (+1 more) |
| `brain_advisory_audit` | 57 | 11 | idx_brain_audit_train | 1 write site(s): api\brain.py:198 |
| `breathalyzer_tests` | 12 | 11 | idx_ba_staff | 1 write site(s): api\workforce_routes.py:52 |
| `cleaning_logs` | 9 | 9 | idx_clean_stn | 2 write site(s): api\infra_routes.py:419, api\infra_routes.py:466 |
| `commercial_stalls` | 1 | 12 | idx_stalls_station | 2 write site(s): api\commercial_routes.py:275, api\commercial_routes.py:339 |
| `conformal_pid_state` | 0 | 7 | None (PK only) | NONE (read-only/orphan) |
| `corridor_sections` | 4 | 7 | idx_corr_sec_stns | 1 write site(s): api\section_routes.py:57 |
| `crew_rosters` | 10 | 13 | idx_crew_stn_status | 2 write site(s): api\workforce_routes.py:171, api\workforce_routes.py:281 |
| `cross_station_locks` | 6 | 11 | idx_cross_locks_sec | 1 write site(s): api\section_routes.py:91 |
| `delay_certificates` | 10 | 14 | idx_delay_certs_qr, idx_delay_certs_train | 1 write site(s): api\commercial_routes.py:80 |
| `eta_prediction_ledger` | 3050 | 15 | idx_ledger_hash, idx_ledger_train | 2 write site(s): engine\prediction_ledger.py:83, scripts\repair_ledger.py:57 |
| `handover_log` | 7 | 14 | idx_handover_station_date | 1 write site(s): api\handover_routes.py:211 |
| `hist_baselines` | 1200 | 7 | idx_hist_baselines | 2 write site(s): data\db.py:98, data\db.py:98 |
| `incidents` | 6 | 11 | idx_incidents_stn | 1 write site(s): api\safety_routes.py:431 |
| `level_crossings` | 4 | 10 | idx_lc_stn | 1 write site(s): api\safety_routes.py:732 |
| `live_delay_ledger` | 222 | 13 | idx_live_delay_ledger_timestamp, idx_live_delay_ledger_train | 1 write site(s): data\db.py:368 |
| `live_ingest_events` | 0 | 7 | idx_live_ingest_lookup | NONE (read-only/orphan) |
| `live_positions` | 752 | 16 | idx_live_positions_updated, idx_live_positions_station | 2 write site(s): data\db.py:251, data\db.py:288 |
| `lost_and_found` | 10 | 14 | idx_lost_found_stn | 1 write site(s): api\commercial_routes.py:394 |
| `notification_ack` | 6 | 6 | idx_notif_ack_notif | 1 write site(s): notifications\dispatcher.py:331 |
| `notification_log` | 56 | 9 | idx_notif_log_sent, idx_notif_log_staff | 1 write site(s): notifications\channels\inapp.py:47 |
| `notifications` | 129 | 13 | idx_notifications_station_state, idx_notifications_created, idx_notifications_role_state | 1 write site(s): notifications\dispatcher.py:257 |
| `planner_changesets` | 6 | 8 | idx_planner_changesets_stn | 1 write site(s): api\planner_routes.py:135 |
| `platform_assignments` | 18 | 11 | idx_pf_assign_stn | 2 write site(s): api\planner_routes.py:125, api\platform_routes.py:204 |
| `platform_states` | 2 | 7 | None (PK only) | 4 write site(s): api\ops_routes.py:111, api\ops_routes.py:196 (+2 more) |
| `possessions` | 6 | 16 | idx_possessions_stn_time | 1 write site(s): api\safety_routes.py:199 |
| `rake_links` | 14 | 4 | None (PK only) | 2 write site(s): data\seed.py:246, data\seed.py:246 |
| `rakes` | 4 | 12 | idx_rakes_train | 2 write site(s): api\infra_routes.py:51, api\infra_routes.py:114 |
| `roles` | 9 | 4 | None (PK only) | 1 write site(s): data\seed_users.py:124 |
| `route_stations` | 1205 | 7 | None (PK only) | 3 write site(s): data\seed.py:233, data\seed.py:233 (+1 more) |
| `run_snapshots` | 25 | 14 | idx_snapshots_ts, idx_snapshots_run_ts | 1 write site(s): collector\snapshot_cron.py:112 |
| `sahayak_roster` | 5 | 10 | idx_sahayak_stn | 1 write site(s): api\workforce_routes.py:468 |
| `schema_migrations` | 14 | 3 | None (PK only) | 1 write site(s): data\db.py:157 |
| `section_advisories` | 0 | 12 | idx_sec_adv_stn | NONE (read-only/orphan) |
| `sections` | 14 | 7 | None (PK only) | 8 write site(s): data\seed.py:94, data\seed.py:94 (+6 more) |
| `shadow_log` | 0 | 10 | None (PK only) | NONE (read-only/orphan) |
| `shunting_moves` | 6 | 13 | idx_shunting_stn_time | 1 write site(s): api\ops_routes.py:316 |
| `sim_ledger` | 3001 | 8 | idx_ledger_run_train | 1 write site(s): engine\simulator.py:295 |
| `sop_runs` | 6 | 10 | idx_sop_runs_stn | 1 write site(s): api\safety_routes.py:572 |
| `speed_restrictions` | 13 | 14 | idx_tsr_section_status | 4 write site(s): api\safety_routes.py:55, api\safety_routes.py:157 (+2 more) |
| `staff` | 10 | 7 | idx_staff_lookup | 2 write site(s): data\seed.py:258, data\seed.py:258 |
| `staff_shifts` | 6 | 9 | idx_shifts_stn_date | 2 write site(s): api\workforce_routes.py:356, api\workforce_routes.py:414 |
| `station_assets` | 6 | 9 | idx_assets_stn_type | 4 write site(s): api\infra_routes.py:162, api\infra_routes.py:224 (+2 more) |
| `station_events` | 33601 | 13 | idx_events_train_event_time, idx_events_station_date, idx_events_train_date, idx_events_date, idx_events_lookup | 16 write site(s): collector\collect.py:102, collector\collect.py:102 (+14 more) |
| `stations` | 112 | 8 | None (PK only) | 3 write site(s): data\seed.py:56, scripts\clean_and_curate_real_data.py:344 (+1 more) |
| `timetable_entries` | 6 | 15 | idx_tt_entries_stn, idx_tt_entries_version | 3 write site(s): api\timetable_routes.py:228, api\timetable_routes.py:337 (+1 more) |
| `timetable_versions` | 6 | 9 | None (PK only) | 2 write site(s): api\timetable_routes.py:112, api\timetable_routes.py:467 |
| `train_runs` | 5 | 7 | idx_train_runs_train_date | 1 write site(s): collector\snapshot_cron.py:98 |
| `trains` | 151 | 6 | None (PK only) | 3 write site(s): data\seed.py:116, scripts\clean_and_curate_real_data.py:349 (+1 more) |
| `user_roles` | 10 | 2 | None (PK only) | 3 write site(s): api\admin_routes.py:223, api\admin_routes.py:310 (+1 more) |
| `users` | 10 | 9 | idx_users_station, idx_users_role, idx_users_username | 5 write site(s): api\admin_routes.py:208, api\admin_routes.py:295 (+3 more) |
| `weather` | 3080 | 12 | None (PK only) | 10 write site(s): collector\weather.py:126, collector\weather.py:126 (+8 more) |
| `weather_hourly` | 1 | 10 | idx_weather_hourly_ts, idx_weather_hourly_date | 4 write site(s): collector\weather_backfill.py:209, collector\weather_backfill.py:209 (+2 more) |
| `work_orders` | 6 | 11 | idx_work_orders_stn | 1 write site(s): api\infra_routes.py:271 |

---

## 0.3 ARTIFACT INVENTORY (ml/artifacts/)

| Artifact Filename | Size | Code References | Primary Consumer | Boot Impact If Missing |
|---|---|---|---|---|
| `artifact_integrity.json` | 862 bytes | 2 call site(s) | `api\routes.py` | CRITICAL: /v1/health reports models unavailable, ready=False; production raises RuntimeError |
| `candidate0_manifest.json` | 3,125 bytes | 0 call site(s) | `Unreferenced / Static output` | INFORMATIONAL: Evaluator or diagnostic output artifact |
| `candidate0_metrics.json` | 7,220 bytes | 3 call site(s) | `scripts\candidate_shootout.py` | INFORMATIONAL: Evaluator or diagnostic output artifact |
| `drift_report.json` | 1,755 bytes | 4 call site(s) | `api\routes.py` | LOW: /v1/health defaults drift status to GREEN and model trust to HIGH |
| `gru_config.json` | 364 bytes | 2 call site(s) | `ml\audit.py` | INFORMATIONAL: Evaluator or diagnostic output artifact |
| `manifest.json` | 2,696 bytes | 19 call site(s) | `api\predictor.py` | CRITICAL: /v1/health reports models unavailable, ready=False; production raises RuntimeError |
| `metrics.json` | 9,855 bytes | 30 call site(s) | `api\routes.py` | CRITICAL: /v1/health reports models unavailable, ready=False; production raises RuntimeError |
| `model_delta_q10.txt` | 4,208,090 bytes | 1 call site(s) | `ml\artifact_integrity.py` | INFORMATIONAL: Evaluator or diagnostic output artifact |
| `model_delta_q50.txt` | 4,178,791 bytes | 1 call site(s) | `ml\artifact_integrity.py` | INFORMATIONAL: Evaluator or diagnostic output artifact |
| `model_delta_q90.txt` | 4,163,736 bytes | 1 call site(s) | `ml\artifact_integrity.py` | INFORMATIONAL: Evaluator or diagnostic output artifact |
| `model_direct_q10.txt` | 4,192,390 bytes | 5 call site(s) | `api\routes.py` | CRITICAL: /v1/health reports models unavailable, ready=False; production raises RuntimeError |
| `model_direct_q50.txt` | 4,167,743 bytes | 9 call site(s) | `api\predictor.py` | CRITICAL: /v1/health reports models unavailable, ready=False; production raises RuntimeError |
| `model_direct_q90.txt` | 4,176,807 bytes | 5 call site(s) | `api\routes.py` | CRITICAL: /v1/health reports models unavailable, ready=False; production raises RuntimeError |
| `model_gru_challenger.pt` | 937,363 bytes | 8 call site(s) | `api\predictor.py` | HIGH: GRU Challenger fails to load, logs warning, challenger fallback fails |
| `model_lr_benchmark.pkl` | 1,791 bytes | 5 call site(s) | `ml\artifact_integrity.py` | MEDIUM: Linear regression baseline model fails in evaluate.py / ensemble.py |
| `perf_bench.json` | 407 bytes | 1 call site(s) | `scripts\perf_bench.py` | INFORMATIONAL: Evaluator or diagnostic output artifact |
| `registry.json` | 909 bytes | 12 call site(s) | `api\predictor.py` | HIGH: Falls back to hardcoded champion 'LightGBM_Quantile_Direct' |
| `shootout_results.json` | 3,432 bytes | 1 call site(s) | `scripts\candidate_shootout.py` | INFORMATIONAL: Evaluator or diagnostic output artifact |

---

## 0.4 STARTUP TRACE & LIFECYCLE ORDER

### Execution Sequence in `api/main.py:lifespan`:
1. **Threadpool Configuration**: `torch.set_num_threads(1)` caps torch execution to 1 thread to avoid thread contention.
2. **Database Initialization**: `db = get_db(); db.init_schema()` validates DB file, runs DDL, and applies outstanding migrations from `scripts/migrations/*.sql`.
3. **Historical Baseline Materialization**: `db.materialize_historical_baselines()` runs aggregate queries to populate `hist_baselines` table.
4. **Row Count Telemetry**: `counts = db.table_counts()` logs loaded station events count.
5. **Background Tracker Start**: `tracker = get_live_tracker(db); await tracker.start()` launches asyncio background task `_run_loop()`.
6. **Model Loading Pattern**: **LAZY ON-DEMAND**. Models are NOT eagerly loaded in `lifespan`. They are initialized on the first inbound request to `/v1/health` or `/v1/trains/{train_no}/eta` via `get_predictor_service()`.
7. **Import-Time Side Effects**: **0**. Probe script detected zero database queries or network socket connections at module import time.

---

## 0.5 BACKGROUND PROCESSES

| Process / Task Name | Type | Started By | Supervised / Survives Errors? | Graceful Shutdown? | Multi-Worker / Reload Hazard |
|---|---|---|---|---|---|
| `LiveTracker._run_loop()` | `asyncio.Task` (`engine/live_tracker.py:191`) | `lifespan` startup (`api/main.py:68`) | YES (`except Exception: pass` inside loop) | YES (`await tracker.stop()` cancels task on shutdown) | **HIGH**: If running multiple uvicorn workers (e.g. `-w 4`), each worker executes `lifespan` and launches an independent tracker loop writing concurrently to SQLite |

---

## 0.6 FRONTEND CONTRACT LIST & CROSS-LAYER PARITY

Total Unique Frontend Endpoints: **37**
Matching Backend Routes: **33**
Contract Mismatches: **4**

### Definite Contract Mismatches Found
| Frontend Endpoint Call | Frontend Source | Backend Route Status | Severity | Failure Impact |
|---|---|---|---|---|
| `POST /api/platform/rollback` | `web/src/lib/api.ts:624` | **NONEXISTENT ROUTE** | **HIGH** | UI button for platform rollback throws 404/405 |
| `POST /api/safety/tsr/${id}/lift` | `web/src/lib/api.ts:841` | Backend route is `DELETE /api/safety/tsr/{tsr_id}` | **HIGH** | UI 'Lift TSR' action sends POST .../lift, returns 405 Method Not Allowed |
| `POST /api/section/handoffs/${id}/ack` | `web/src/lib/api.ts:876` | Backend route is `PUT /handoff/{lock_id}/grant` | **HIGH** | Section controller handoff acknowledgement fails with 404 Not Found |
| `POST /api/workforce/crew/signon` | `web/src/lib/api.ts:747` | Backend route is `POST /api/workforce/crew/sign-on` (hyphenated) | **HIGH** | Crew sign-on submission fails with 404 Not Found |
