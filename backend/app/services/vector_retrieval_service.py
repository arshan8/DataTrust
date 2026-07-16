from functools import lru_cache

from app.db.postgres_client import get_pg_connection
from app.services.embedding_service import generate_embedding
from app.services.resource_scope_service import get_allowed_resource_scopes
from app.services.orchestrator_service import choose_sources


def _vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{v:.8f}" for v in values) + "]"


@lru_cache(maxsize=256)
def _cached_query_embedding(query: str) -> tuple[float, ...]:
    return tuple(generate_embedding(query))


def retrieve_authorized_chunks(query: str, user_context: dict, top_k: int = 5) -> dict:
    allowed_scopes = get_allowed_resource_scopes(user_context)
    selected_sources, reasoning = choose_sources(query, allowed_scopes, user_context)

    allowed_scope_ids = [
        s["scope_id"]
        for s in allowed_scopes
        if s["source_type"] in selected_sources
    ]

    if not allowed_scope_ids:
        return {
            "selected_sources": selected_sources,
            "selection_reasoning": reasoning,
            "chunks": [],
        }

    query_embedding = list(_cached_query_embedding(query.strip()))
    vector_value = _vector_literal(query_embedding)

    sql = """
        select
            dc.id as chunk_id,
            dc.document_id,
            dc.chunk_text,
            dc.resource_path,
            d.title,
            ss.code as source_type,
            coalesce(rs.resource_name, d.title) as resource_name,
            (dc.embedding <=> %s::vector) as distance
        from document_chunks dc
        join documents d on d.id = dc.document_id
        join source_systems ss on ss.id = dc.source_system_id
        left join resource_scopes rs on rs.id = dc.resource_scope_id
        join auth_levels al on al.id = dc.min_auth_level_id
        join departments dep on dep.id = dc.department_id
        where dc.is_active = true
          and dc.resource_scope_id = any(%s)
          and al.rank <= %s
          and dep.code = %s
          and ss.code = any(%s)
        order by dc.embedding <=> %s::vector
        limit %s
    """

    with get_pg_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql,
                (
                    vector_value,
                    allowed_scope_ids,
                    user_context["auth_rank"],
                    user_context["department"],
                    selected_sources,
                    vector_value,
                    top_k,
                ),
            )
            rows = cur.fetchall()

    chunks = []
    for row in rows:
        chunks.append({
            "chunk_id": row[0],
            "document_id": row[1],
            "chunk_text": row[2],
            "resource_path": row[3],
            "title": row[4],
            "source_type": row[5],
            "resource_name": row[6],
            "score": float(row[7]),
        })

    return {
        "selected_sources": selected_sources,
        "selection_reasoning": reasoning,
        "chunks": chunks,
    }
# from typing import List
# from app.db.postgres_client import get_pg_connection
# from app.services.embedding_service import generate_embedding
# from app.services.resource_scope_service import get_allowed_resource_scopes
# from app.services.orchestrator_service import choose_sources


# def _vector_literal(values: list[float]) -> str:
#     return "[" + ",".join(f"{v:.8f}" for v in values) + "]"


# def retrieve_authorized_chunks(query: str, user_context: dict, top_k: int = 5) -> dict:
#     # if department != "TECH":
#     #     allowed_scopes = [
#     #         s for s in allowed_scopes
#     #         if s.get("source_type") != "GITHUB"
#     #     ]
#     allowed_scopes = get_allowed_resource_scopes(user_context)
#     #selected_sources, reasoning = choose_sources(query, allowed_scopes)
#     selected_sources, reasoning = choose_sources(query, allowed_scopes, user_context)
#     # department = user_context.get("department")

    
#     allowed_scope_ids = [s["scope_id"] for s in allowed_scopes if s["source_type"] in selected_sources]

#     if not allowed_scope_ids:
#         return {
#             "selected_sources": selected_sources,
#             "selection_reasoning": reasoning,
#             "chunks": []
#         }

#     query_embedding = generate_embedding(query)
#     vector_value = _vector_literal(query_embedding)

#     sql = """
#         select
#             dc.id as chunk_id,
#             dc.document_id,
#             dc.chunk_text,
#             dc.resource_path,
#             d.title,
#             ss.code as source_type,
#             coalesce(rs.resource_name, d.title) as resource_name,
#             (dc.embedding <=> %s::vector) as distance
#         from document_chunks dc
#         join documents d on d.id = dc.document_id
#         join source_systems ss on ss.id = dc.source_system_id
#         left join resource_scopes rs on rs.id = dc.resource_scope_id
#         join auth_levels al on al.id = dc.min_auth_level_id
#         where dc.is_active = true
#           and dc.resource_scope_id = any(%s)
#           and al.rank <= %s
#           and ss.code = any(%s)
#         order by dc.embedding <=> %s::vector
#         limit %s
#     """

#     with get_pg_connection() as conn:
#         with conn.cursor() as cur:
#             cur.execute(
#                 sql,
#                 (
#                     vector_value,
#                     allowed_scope_ids,
#                     user_context["auth_rank"],
#                     selected_sources,
#                     vector_value,
#                     top_k,
#                 ),
#             )
#             rows = cur.fetchall()

#     chunks = []
#     for row in rows:
#         chunks.append({
#             "chunk_id": row[0],
#             "document_id": row[1],
#             "chunk_text": row[2],
#             "resource_path": row[3],
#             "title": row[4],
#             "source_type": row[5],
#             "resource_name": row[6],
#             "score": float(row[7]),
#         })

#     return {
#         "selected_sources": selected_sources,
#         "selection_reasoning": reasoning,
#         "chunks": chunks
#     }