WITH unique_prompt_metrics AS (
    SELECT DISTINCT
        p.content,
        r.project,
        r.brand_name,
        r.model_channel_id,
        r.visibility_count,
        r.visibility_total,
        r.date
    FROM `bhep-data-resources.dbt_production.int_peec_brands_report` AS r
    LEFT JOIN `bhep-data-resources.dbt_production.int_peec_prompts` AS p 
        ON p.prompt_id = r.prompt_id
    WHERE r.project = 'Yorkville University'
      AND r.date BETWEEN '2026-06-08' AND '2026-06-14'
),

b AS (
    SELECT 
        upm.project,
        upm.brand_name,
        upm.content,
        SAFE_DIVIDE(SUM(upm.visibility_count), SUM(upm.visibility_total)) AS visibility
    FROM unique_prompt_metrics AS upm
    GROUP BY 1, 2, 3
),

c AS (
    SELECT 
        *,
        MAX(visibility) OVER (PARTITION BY content) AS max_vis,
        MAX(
            CASE 
                WHEN brand_name = 'Yorkville University' 
                THEN visibility 
                ELSE 0 
            END
        ) OVER (PARTITION BY content) AS yorkville_vis
    FROM b
),

d AS (
    SELECT
        content,
        yorkville_vis,
        max_vis,
        STRING_AGG(
            brand_name,
            ', '
            ORDER BY visibility DESC
        ) AS brands_higher_than_yorkville
    FROM c
    WHERE visibility > yorkville_vis
    GROUP BY 1, 2, 3
)

SELECT
    d.content,
    prompts.prompt_id,
    d.yorkville_vis,
    d.max_vis,
    d.brands_higher_than_yorkville
FROM d
left join `bhep-data-resources.dbt_production.int_peec_prompts` AS prompts on prompts.content = d.content
WHERE max_vis != yorkville_vis
ORDER BY content;