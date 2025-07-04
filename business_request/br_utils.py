from typing import List, Optional

from business_request.br_fields import BRFields
from business_request.br_models import BRQueryFilter

__all__ = ["get_br_query"]

def get_br_query(br_number_count: int = 0,
                status: int = 0,
                limit: bool = False,
                active: bool = True,
                br_filters: Optional[List[BRQueryFilter]] = None) -> str:
    """Function that will build the select statement for retrieving BRs
    
    Parameters order for the execute query should be as follow:
    
    1) statuses
    2) all thw other fields value
    3) limit for TOP()
    
    """

    query = """
    DECLARE @MAX_DATE DATETIME = (SELECT MAX(PERIOD_END_DATE) FROM [EDR_CARZ].[FCT_DEMAND_BR_SNAPSHOT]);

    WITH FilteredResults AS (
    SELECT
    """

    # Default select statement from BR_ITEMS & other tables
    query += "br.BR_NMBR as BR_NMBR, br.EXTRACTION_DATE as EXTRACTION_DATE, " + ", ".join([f"{value['db_field']} as {key}" for key, value in BRFields.valid_search_fields.items()])

    # Default FROM statement
    query += """
    FROM
        [EDR_CARZ].[DIM_DEMAND_BR_ITEMS] br
    """

    # Processing BR SNAPSHOT clause
    snapshot_where_clause = ["snp.PERIOD_END_DATE = @MAX_DATE"]
    if status:
        placeholders = ", ".join(["%s"] * status)
        snapshot_where_clause.append(f"snp.STATUS_ID IN ({placeholders})")

    snapshot_where_clause = " AND ".join(snapshot_where_clause)
    query += f"""
    INNER JOIN
        [EDR_CARZ].[FCT_DEMAND_BR_SNAPSHOT] snp
    ON snp.BR_NMBR = br.BR_NMBR AND {snapshot_where_clause}
    """

    # Processing BR STATUS clause
    query += """
    INNER JOIN
        [EDR_CARZ].[DIM_BITS_STATUS] s
    ON s.STATUS_ID = snp.STATUS_ID
    """

    # Processing BR OPIS clause - Using CASE statements with better join logic
    query += """
    LEFT JOIN
        (SELECT
            BR_NMBR,
            ACC_MANAGER_OPI,
            AGR_OPI,
            BA_OPI,
            BA_PRICING_OPI,
            BA_PRICING_TL,
            BA_TL,
            CSM_DIRECTOR,
            EAOPI,
            PM_OPI,
            PROD_OPI,
            QA_OPI,
            SDM_TL_OPI,
            SISDOPI,
            SR_OWNER as BR_OWNER,
            TEAMLEADER,
            WIO_OPI
        FROM
        (
            SELECT opis.BR_NMBR, opis.BUS_OPI_ID, person.FULL_NAME
            FROM [EDR_CARZ].[FCT_DEMAND_BR_OPIS] opis
            INNER JOIN [EDR_CARZ].[DIM_BITS_PERSON] person
            ON opis.PERSON_ID = person.PERSON_ID
        ) AS SourceTable
        PIVOT
        (
            MAX(FULL_NAME)
            FOR BUS_OPI_ID IN (
                ACC_MANAGER_OPI,
                AGR_OPI,
                BA_OPI,
                BA_PRICING_OPI,
                BA_PRICING_TL,
                BA_TL,
                CSM_DIRECTOR,
                EAOPI,
                PM_OPI,
                PROD_OPI,
                QA_OPI,
                SDM_TL_OPI,
                SISDOPI,
                SR_OWNER,
                TEAMLEADER,
                WIO_OPI
            )
        ) AS PivotTable
    ) AS opis
    ON opis.BR_NMBR = br.BR_NMBR
    """

    # PRODUCTS - Optimized with better join hint
    query += """
    LEFT JOIN
        (SELECT BR_NMBR, PROD_ID 
         FROM [EDR_CARZ].[FCT_DEMAND_BR_PRODUCTS] WITH (FORCESEEK)
         WHERE PROD_TYPE = 'LEAD') br_products
    ON br_products.BR_NMBR = br.BR_NMBR
    LEFT JOIN [EDR_CARZ].[DIM_BITS_PRODUCT] products WITH (NOLOCK)
    ON products.PROD_ID = br_products.PROD_ID
    """

    # WHERE CLAUSE PROCESSING (BR_NMBR and ACTIVE, etc)
    base_where_clause = []
    if active:
        base_where_clause.append("s.BR_ACTIVE_EN = 'Active'")

    if br_number_count:
        # Prevents SQL injection, this only calculates the placehoders ... i.e; BR_NMBR IN (%s, %s, %s)
        placeholders = ", ".join(["%s"] * br_number_count)
        base_where_clause.append(f"br.BR_NMBR IN ({placeholders})")

    if br_filters:
        for br_filter in br_filters:
            field_name = BRFields.valid_search_fields.get(br_filter.name)
            if field_name:
                if br_filter.is_date():
                    # Handle date fields
                    base_where_clause.append(f"CONVERT(DATE, {field_name['db_field']}) {br_filter.operator} %s")
                else:
                    # Handle other fields, defaulting to LIKE operator since they are mostly strings ...
                    base_where_clause.append(f"{field_name['db_field']} LIKE %s")

    if base_where_clause:
        query += "WHERE " + " AND ".join(base_where_clause)

    # Wrap CTE statement
    query += """)
    SELECT {top} *,
        COUNT(*) OVER() AS TotalCount
    FROM FilteredResults
    """.replace("{top}", "TOP(%d)" if limit else "")

    # ORDER BY clause
    query += """
    ORDER BY
        BR_NMBR DESC
    OPTION (RECOMPILE, OPTIMIZE FOR (@MAX_DATE UNKNOWN))
    """
    return query
