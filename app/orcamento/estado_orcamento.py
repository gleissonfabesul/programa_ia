from typing import List, TypedDict, Optional

class PendingItem(TypedDict):
    name: str
    quantity: str
    card: str

class AgentState(TypedDict):
    customer_id: int
    cemp: str
    raw_request: str
    outros: bool
    pending_items: List[PendingItem]
    history_pool: List[dict]
    contract_pool: List[dict]
    final_results: List[dict]

class AgentProcessaExcel(TypedDict):
    input_data: str
    generated_code: Optional[str]
    execution_result: Optional[str]
    error_message: Optional[str]
    retry_count: int
    excel_path: Optional[str]