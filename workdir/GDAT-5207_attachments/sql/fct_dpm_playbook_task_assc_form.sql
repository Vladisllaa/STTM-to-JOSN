SELECT
CAST(WORKSPACE_ID AS BIGINT) AS workspace_id,
CAST(PLAYBOOK_ID AS STRING) AS playbook_id,
CAST(TASK_ID AS STRING) AS task_id,
CAST(FORM_PLACEHOLDER_ID AS STRING) AS form_placeholder_id,
CAST(FORM_ID AS STRING) AS form_id,
CAST(FORM_TYPE AS STRING) AS form_type,
CAST(FORM_DUE_DATE AS TIMESTAMP) AS form_due_date,
CAST(FORM_STATUS AS STRING) AS form_status,
CAST(LOAD_DATE AS TIMESTAMP) AS load_date,
CAST(curdate() AS DATE) AS snapshot_date,
CAST(null AS STRING) AS contract_cd
FROM
dpm_playbook_task_assc_form
