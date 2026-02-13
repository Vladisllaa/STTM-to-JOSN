SELECT
CAST(WORKSPACE_ID AS BIGINT) AS workspace_id,
CAST(PLAYBOOK_ID AS STRING) AS playbook_id,
CAST(TASK_ID AS STRING) AS task_id,
CAST(CRITERIA AS STRING) AS criteria,
CAST(TASK_TITLE AS STRING) AS task_title,
CAST(CRITERIA_FIELD AS STRING) AS criteria_field,
CAST(WORKSPACE_ATTRIBUTE_ID AS STRING) AS workspace_attribute_id,
CAST(ATTRIBUTE_VALUE_KEY_ID AS STRING) AS attribute_value_key_id,
CAST(ATTRIBUTE_VALUE_ID AS STRING) AS attribute_value_id,
CAST(LOAD_DATE AS TIMESTAMP) AS load_date,
CAST(curdate() AS DATE) AS snapshot_date,
CAST(null AS STRING) AS contract_cd
FROM
dpm_playbook_task_completion_criteria
