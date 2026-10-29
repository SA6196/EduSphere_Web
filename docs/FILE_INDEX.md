# Source file and function navigation

This index was extracted from the shipped Python AST. Names are navigational hints, **not semantic descriptions**; inspect each function and its callers before changing behavior. Vue files are indexed by path because much of their code lives inside component setup blocks.

## Backend Python modules

| File | Top-level classes/functions |
|---|---|
| `Backend/academics/__init__.py` | `module constants/config` |
| `Backend/academics/apps.py` | `AcademicsConfig` |
| `Backend/academics/quiz_visibility.py` | `quiz_marks_visible_sql(), offering_has_hidden_quiz_sql()` |
| `Backend/academics/repository.py` | `student_dashboard(), instructor_offerings(), admin_summary(), list_courses(), list_offerings(), get_offering(), enroll_student(), my_enrollments(), get_student_id_by_user_id(), get_instructor_id_by_user_id(), +11 more` |
| `Backend/academics/repository_backup_commit43.py` | `student_dashboard(), instructor_offerings(), admin_summary(), list_courses(), list_offerings(), get_offering(), enroll_student(), my_enrollments(), get_student_id_by_user_id(), get_instructor_id_by_user_id()` |
| `Backend/academics/repository_backup_commit434.py` | `student_dashboard(), instructor_offerings(), admin_summary(), list_courses(), list_offerings(), get_offering(), enroll_student(), my_enrollments(), get_student_id_by_user_id(), get_instructor_id_by_user_id()` |
| `Backend/academics/services.py` | `EnrollmentService (1 methods), OfferingService (2 methods), GradeService (2 methods)` |
| `Backend/academics/urls.py` | `module constants/config` |
| `Backend/academics/views.py` | `StudentDashboardView (1 methods), InstructorOfferingsView (1 methods), AdminSummaryView (1 methods), CourseListView (1 methods), OfferingListView (1 methods), OfferingDetailView (1 methods), OfferingGradingView (1 methods), InstructorOfferingRosterView (1 methods), EnrollmentCreateView (1 methods), MyEnrollmentView (1 methods), +4 more` |
| `Backend/accounts/__init__.py` | `module constants/config` |
| `Backend/accounts/apps.py` | `AccountsConfig` |
| `Backend/accounts/authentication.py` | `LMSJWTAuthentication (2 methods)` |
| `Backend/accounts/authorization.py` | `require_role(), require_instructor_ownership()` |
| `Backend/accounts/management/__init__.py` | `module constants/config` |
| `Backend/accounts/management/commands/__init__.py` | `module constants/config` |
| `Backend/accounts/management/commands/set_lms_password.py` | `Command (2 methods)` |
| `Backend/accounts/permissions.py` | `HasRole (1 methods), IsStudent, IsInstructor, IsAdmin, IsInstructorOrAdmin` |
| `Backend/accounts/principal.py` | `LMSPrincipal (3 methods)` |
| `Backend/accounts/registration.py` | `public_programs(), register_student(), activate_student()` |
| `Backend/accounts/repository.py` | `get_user_by_username(), get_user_by_id(), update_last_login(), set_password_hash(), log_activity(), get_student_id_by_user_id(), get_instructor_id_by_user_id()` |
| `Backend/accounts/serializers.py` | `LoginSerializer, RefreshSerializer` |
| `Backend/accounts/tokens.py` | `_now(), create_access_token(), create_refresh_token(), decode_token()` |
| `Backend/accounts/urls.py` | `module constants/config` |
| `Backend/accounts/views.py` | `_client_ip(), _public_user(), LoginView (1 methods), RefreshView (1 methods), MeView (1 methods), SignupThrottle, PublicProgramListView (1 methods), StudentSignupView (1 methods)` |
| `Backend/administration/__init__.py` | `module constants/config` |
| `Backend/administration/apps.py` | `AdministrationConfig` |
| `Backend/administration/compliance.py` | `validated(), save_master_data(), audit_overview()` |
| `Backend/administration/compliance_views.py` | `MasterDataCollectionView (1 methods), MasterDataDetailView (1 methods), AdminAuditView (1 methods), StudentApprovalView (1 methods)` |
| `Backend/administration/repository.py` | `list_departments(), list_programs(), list_students(), list_instructors(), get_program(), get_department(), get_course(), get_semester(), get_offering_admin(), get_offering_instructors(), +10 more` |
| `Backend/administration/services.py` | `_required(), _positive_int(), _money_number(), _password(), _email(), _ensure_unique_identity(), AdminIdentityService (3 methods), AdminOfferingService (3 methods), AdminGradingService (2 methods)` |
| `Backend/administration/urls.py` | `module constants/config` |
| `Backend/administration/views.py` | `AdminDirectoryView (1 methods), AdminStudentAccountsView (2 methods), AdminInstructorAccountsView (2 methods), AdminOfferingCreateView (1 methods), AdminOfferingInstructorView (2 methods), AdminGradingSchemeView (2 methods)` |
| `Backend/announcements/__init__.py` | `module constants/config` |
| `Backend/announcements/apps.py` | `AnnouncementsConfig` |
| `Backend/announcements/repository.py` | `post_announcement(), list_announcements(), get_announcement(), student_has_offering()` |
| `Backend/announcements/services.py` | `AnnouncementService (8 methods)` |
| `Backend/announcements/urls.py` | `module constants/config` |
| `Backend/announcements/views.py` | `AnnouncementCreateView (1 methods), AnnouncementListView (1 methods), AnnouncementDetailView (1 methods)` |
| `Backend/assignments/__init__.py` | `module constants/config` |
| `Backend/assignments/apps.py` | `module constants/config` |
| `Backend/assignments/repository.py` | `get_component(), get_component_offering(), create_assignment(), get_assignments(), get_assignment(), get_latest_submission_version(), create_submission(), get_student_submissions(), instructor_owns_offering(), assignment_exists_for_component(), +1 more` |
| `Backend/assignments/services.py` | `AssignmentService (5 methods)` |
| `Backend/assignments/urls.py` | `module constants/config` |
| `Backend/assignments/views.py` | `AssignmentCreateView (1 methods), AssignmentListView (1 methods), AssignmentSubmissionView (1 methods), StudentSubmissionListView (1 methods), InstructorSubmissionListView (1 methods)` |
| `Backend/attendance/repository.py` | `get_sessions(), get_session(), instructor_owns_offering(), record_attendance(), get_student_attendance(), get_student_attendance_for_offering(), get_offering(), create_class_session(), get_student_semester_attendance()` |
| `Backend/attendance/services.py` | `AttendanceService (6 methods)` |
| `Backend/attendance/urls.py` | `module constants/config` |
| `Backend/attendance/views.py` | `SessionListView (1 methods), SessionCreateView (1 methods), RecordAttendanceView (1 methods), MyAttendanceView (1 methods), MyOfferingAttendanceView (1 methods), MySemesterAttendanceView (1 methods)` |
| `Backend/core/__init__.py` | `module constants/config` |
| `Backend/core/apps.py` | `CoreConfig` |
| `Backend/core/audit.py` | `log_activity()` |
| `Backend/core/constants.py` | `Roles, ActivityTypes, Status` |
| `Backend/core/exception_handler.py` | `_drf_message(), _database_status(), edusphere_exception_handler()` |
| `Backend/core/exceptions.py` | `LMSException, AuthenticationError, PermissionDeniedError, NotFoundError, DatabaseError, ValidationError, BusinessRuleError, EnrollmentError, OfferingNotFoundError, DuplicateEnrollmentError, +1 more` |
| `Backend/core/pagination.py` | `paginate()` |
| `Backend/core/responses.py` | `success_response(), error_response(), paginated_response()` |
| `Backend/core/service_base.py` | `BaseService (2 methods)` |
| `Backend/core/urls.py` | `module constants/config` |
| `Backend/core/validators.py` | `validate_required(), validate_positive_integer(), validate_role()` |
| `Backend/core/views.py` | `HealthView (1 methods), DatabaseHealthView (1 methods), VersionView (1 methods)` |
| `Backend/database/__init__.py` | `module constants/config` |
| `Backend/database/connection.py` | `_count(), connection_statistics(), _connection_string(), _new_connection(), _get_connection(), close_thread_connection(), oracle_request_scope(), _safe_db_error_message(), oracle_connection(), row_to_dict(), +7 more` |
| `Backend/database/errors.py` | `OracleBusinessError, OracleConflictError, OracleForbiddenError, extract_ora_code(), api_exception_from_oracle()` |
| `Backend/database/middleware.py` | `OracleRequestScopeMiddleware (2 methods)` |
| `Backend/database/query.py` | `execute_procedure()` |
| `Backend/database/schema.py` | `object_name()` |
| `Backend/edusphere/__init__.py` | `module constants/config` |
| `Backend/edusphere/asgi.py` | `module constants/config` |
| `Backend/edusphere/settings.py` | `module constants/config` |
| `Backend/edusphere/urls.py` | `module constants/config` |
| `Backend/edusphere/version.py` | `module constants/config` |
| `Backend/edusphere/wsgi.py` | `module constants/config` |
| `Backend/exams/__init__.py` | `module constants/config` |
| `Backend/exams/apps.py` | `ExamsConfig` |
| `Backend/exams/repository.py` | `get_component_context(), get_offering_context(), instructor_owns_offering(), student_has_offering(), get_exam(), get_exam_by_component(), create_exam(), list_exams_for_offering(), student_upcoming_exams()` |
| `Backend/exams/services.py` | `ExamService (10 methods)` |
| `Backend/exams/urls.py` | `module constants/config` |
| `Backend/exams/views.py` | `ExamScheduleCreateView (1 methods), ExamOfferingListView (1 methods), ExamDetailView (1 methods), MyUpcomingExamsView (1 methods)` |
| `Backend/gpa/__init__.py` | `module constants/config` |
| `Backend/gpa/apps.py` | `GpaConfig` |
| `Backend/gpa/repository.py` | `get_student(), get_semester(), get_cgpa(), get_sgpa(), get_sgpa_for_published_semesters(), published_grade_rows()` |
| `Backend/gpa/services.py` | `GPAService (10 methods)` |
| `Backend/gpa/urls.py` | `module constants/config` |
| `Backend/gpa/views.py` | `MyGPASummaryView (1 methods), MySemesterGPAView (1 methods), AdminStudentGPASummaryView (1 methods), AdminStudentSemesterGPAView (1 methods)` |
| `Backend/manage.py` | `main()` |
| `Backend/materials/__init__.py` | `module constants/config` |
| `Backend/materials/repository.py` | `create_material(), get_materials(), get_material()` |
| `Backend/materials/services.py` | `MaterialService (3 methods)` |
| `Backend/materials/urls.py` | `module constants/config` |
| `Backend/materials/views.py` | `MaterialCreateView (1 methods), MaterialListView (1 methods), MaterialDetailView (1 methods)` |
| `Backend/quiz/__init__.py` | `module constants/config` |
| `Backend/quiz/apps.py` | `QuizConfig` |
| `Backend/quiz/auto_grader.py` | `_d(), _normalize(), _score_question(), _in_clause(), load_attempt_for_grading(), load_recorder_user_id(), load_questions(), load_responses(), lock_quiz_enrollment(), synchronize_quiz_component_mark(), +1 more` |
| `Backend/quiz/management/__init__.py` | `module constants/config` |
| `Backend/quiz/management/commands/__init__.py` | `module constants/config` |
| `Backend/quiz/management/commands/audit_legacy_quiz_grades.py` | `_num(), get_legacy_audit_rows(), _sync_one(), Command (2 methods)` |
| `Backend/quiz/repository.py` | `create_quiz(), get_quiz(), get_quiz_context(), get_quizzes(), update_quiz_visibility(), quiz_exists_for_component(), get_question_by_text_type(), get_question(), list_questions(), list_questions_for_instructor(), +41 more` |
| `Backend/quiz/services.py` | `_student_option_token(), _student_option_shuffle(), _resolve_student_option_ids(), QuizService (23 methods)` |
| `Backend/quiz/urls.py` | `module constants/config` |
| `Backend/quiz/views.py` | `QuizCreateView (1 methods), QuizListView (1 methods), QuizContentView (1 methods), QuizVisibilityView (1 methods), QuizAttemptView (1 methods), QuizResponseView (1 methods), QuestionListView (1 methods), QuestionDetailView (1 methods), QuestionCreateView (1 methods), QuestionOptionCreateView (1 methods), +12 more` |
| `Backend/reports/__init__.py` | `module constants/config` |
| `Backend/reports/apps.py` | `ReportsConfig` |
| `Backend/reports/repository.py` | `admin_overview(), list_semesters(), get_offering(), offering_roster(), get_student(), get_semester(), student_progress(), student_sgpa(), student_cgpa(), student_upcoming_exams()` |
| `Backend/reports/services.py` | `ReportService (6 methods)` |
| `Backend/reports/urls.py` | `module constants/config` |
| `Backend/reports/views.py` | `AdminOverviewReportView (1 methods), SemesterListReportView (1 methods), OfferingRosterReportView (1 methods), StudentProgressReportView (1 methods), StudentUpcomingExamsReportView (1 methods)` |
| `Backend/scripts/admin_management_code_audit.py` | `module constants/config` |
| `Backend/scripts/check_odbc_driver.py` | `module constants/config` |
| `Backend/scripts/final_code_audit.py` | `pyfiles()` |
| `Backend/scripts/frontend_readiness_code_audit.py` | `require()` |
| `Backend/scripts/startup_check.py` | `check_environment(), check_database()` |
| `Backend/scripts/test_odbc.py` | `module constants/config` |

## Frontend Vue components and JS

| File | Type |
|---|---|
| `Frontend/src/App.vue` | Vue component |
| `Frontend/src/components/AppShell.vue` | Vue component |
| `Frontend/src/components/AttendanceAnalytics.vue` | Vue component |
| `Frontend/src/components/BarChart.vue` | Vue component |
| `Frontend/src/components/CalendarMonth.vue` | Vue component |
| `Frontend/src/components/ConfirmDialog.vue` | Vue component |
| `Frontend/src/components/DataTable.vue` | Vue component |
| `Frontend/src/components/EmptyState.vue` | Vue component |
| `Frontend/src/components/ErrorState.vue` | Vue component |
| `Frontend/src/components/FileUrlField.vue` | Vue component |
| `Frontend/src/components/LoadingState.vue` | Vue component |
| `Frontend/src/components/SectionCard.vue` | Vue component |
| `Frontend/src/components/StatCard.vue` | Vue component |
| `Frontend/src/components/StatusBadge.vue` | Vue component |
| `Frontend/src/components/ToastHost.vue` | Vue component |
| `Frontend/src/components/workspace/WorkspaceAnnouncementsTab.vue` | Vue component |
| `Frontend/src/components/workspace/WorkspaceAssignmentsTab.vue` | Vue component |
| `Frontend/src/components/workspace/WorkspaceAttendanceTab.vue` | Vue component |
| `Frontend/src/components/workspace/WorkspaceExamsTab.vue` | Vue component |
| `Frontend/src/components/workspace/WorkspaceMaterialsTab.vue` | Vue component |
| `Frontend/src/components/workspace/WorkspaceOverviewTab.vue` | Vue component |
| `Frontend/src/components/workspace/WorkspaceQuizzesTab.vue` | Vue component |
| `Frontend/src/components/workspace/WorkspaceRecordAttendanceTab.vue` | Vue component |
| `Frontend/src/components/workspace/WorkspaceRosterGradingTab.vue` | Vue component |
| `Frontend/src/components/workspace/WorkspaceSchemeEditorTab.vue` | Vue component |
| `Frontend/src/components/workspace/WorkspaceSessionsTab.vue` | Vue component |
| `Frontend/src/main.js` | JavaScript module |
| `Frontend/src/router/index.js` | JavaScript module |
| `Frontend/src/services/api.js` | JavaScript module |
| `Frontend/src/services/http.js` | JavaScript module |
| `Frontend/src/stores/auth.js` | JavaScript module |
| `Frontend/src/stores/toast.js` | JavaScript module |
| `Frontend/src/utils/attendancePredictor.js` | JavaScript module |
| `Frontend/src/utils/errors.js` | JavaScript module |
| `Frontend/src/utils/format.js` | JavaScript module |
| `Frontend/src/utils/roles.js` | JavaScript module |
| `Frontend/src/views/CatalogView.vue` | Vue component |
| `Frontend/src/views/LoginView.vue` | Vue component |
| `Frontend/src/views/NotFoundView.vue` | Vue component |
| `Frontend/src/views/OfferingWorkspaceView.vue` | Vue component |
| `Frontend/src/views/ProfileView.vue` | Vue component |
| `Frontend/src/views/SignupView.vue` | Vue component |
| `Frontend/src/views/admin/AdminDashboardView.vue` | Vue component |
| `Frontend/src/views/admin/AdminManagementView.vue` | Vue component |
| `Frontend/src/views/admin/AdminReportsView.vue` | Vue component |
| `Frontend/src/views/instructor/InstructorDashboardView.vue` | Vue component |
| `Frontend/src/views/instructor/QuestionBankView.vue` | Vue component |
| `Frontend/src/views/instructor/QuizGradingView.vue` | Vue component |
| `Frontend/src/views/student/QuizAttemptView.vue` | Vue component |
| `Frontend/src/views/student/StudentAttendanceView.vue` | Vue component |
| `Frontend/src/views/student/StudentDashboardView.vue` | Vue component |
| `Frontend/src/views/student/StudentPerformanceView.vue` | Vue component |
| `Frontend/src/views/student/StudentQuizAttemptsView.vue` | Vue component |

Total indexed backend Python files: **112**. Indexed top-level methods/functions (approximate): **434**. Use `docs/API_ROUTES.md` for the Django URL map.
