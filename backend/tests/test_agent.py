"""The support agent loop with a scripted LLM: the tool calls are real and run against the database
with the signed-in customer's permissions. This is where "never show another customer's data" is
tested at the AI level: whatever the model asks for, the tools only return the user's own data."""

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.support_agent import FALLBACK_REPLY, SupportAgent
from app.models import SupportTicket, TicketPriority, User
from app.rag.embeddings import Embedder
from app.rag.rag_service import NOT_FOUND_MESSAGE as NOT_FOUND
from app.tools.support_tools import SupportTools
from tests.conftest import ingest, make_order
from tests.fakes import ScriptedLLM, text_turn, tool_results, tool_turn
from tests.helpers_pdf import RETURNS_PDF_SECTIONS, make_pdf


def run(db: Session, user: User, embedder: Embedder, llm: ScriptedLLM, message: str = "Hi"):  # type: ignore[no-untyped-def]
    return SupportAgent(llm, SupportTools(db, user, embedder), user, max_tool_rounds=3).run([], message)


def results_of_round(llm: ScriptedLLM, index: int) -> list[dict[str, Any]]:
    return tool_results(llm.calls[index])


def test_agent_looks_up_the_customers_own_order(db: Session, embedder: Embedder, alice: User) -> None:
    order = make_order(db, alice.customer)  # type: ignore[arg-type]
    llm = ScriptedLLM(tool_turn(("get_order_status", {"order_id": f"#{order.id}"})), text_turn(f"Order #{order.id} is shipped."))
    result = run(db, alice, embedder, llm, f"Where is order {order.id}?")

    assert result.text == f"Order #{order.id} is shipped."
    [record] = result.tool_calls
    assert record.name == "get_order_status" and record.status == "ok"
    assert record.summary == f"Order #{order.id}: shipped"
    [sent] = results_of_round(llm, 1)
    data = json.loads(sent["content"])
    assert data["order_id"] == order.id and data["tracking_number"] == "PO123456789"
    assert sent["is_error"] is False
    assert llm.calls[0]["tools"] and "Alice" in llm.calls[0]["system"]


def test_agent_cannot_read_another_customers_order(db: Session, embedder: Embedder, alice: User, bob: User) -> None:
    bobs_order = make_order(db, bob.customer)  # type: ignore[arg-type]
    llm = ScriptedLLM(tool_turn(("get_order_status", {"order_id": str(bobs_order.id)})), text_turn("I couldn't find that order."))
    result = run(db, alice, embedder, llm)

    assert result.tool_calls[0].status == "error"
    [sent] = results_of_round(llm, 1)
    assert sent["is_error"] is True
    assert "not found" in sent["content"].lower()
    assert "PO123456789" not in sent["content"]  # none of Bob's order details reach the model


def test_agent_cannot_name_another_customer_id(db: Session, embedder: Embedder, alice: User, bob: User) -> None:
    make_order(db, bob.customer)  # type: ignore[arg-type]
    llm = ScriptedLLM(
        tool_turn(("get_customer_orders", {"customer_id": bob.customer.id}), ("get_support_tickets", {"customer_id": bob.customer.id})),  # type: ignore[union-attr]
        text_turn("I can only see your own account."),
    )
    result = run(db, alice, embedder, llm)
    assert [c.status for c in result.tool_calls] == ["error", "error"]
    assert all(r["is_error"] for r in results_of_round(llm, 1))


def test_customer_orders_only_lists_own_orders(db: Session, embedder: Embedder, alice: User, bob: User) -> None:
    own = make_order(db, alice.customer)  # type: ignore[arg-type]
    make_order(db, bob.customer)  # type: ignore[arg-type]
    llm = ScriptedLLM(tool_turn(("get_customer_orders", {})), text_turn("You have one order."))
    run(db, alice, embedder, llm)
    data = json.loads(results_of_round(llm, 1)[0]["content"])
    assert data["total"] == 1 and [o["order_id"] for o in data["orders"]] == [own.id]


def test_agent_creates_a_ticket_for_a_damaged_item(db: Session, embedder: Embedder, alice: User) -> None:
    order = make_order(db, alice.customer)  # type: ignore[arg-type]
    args = {
        "subject": "Mug arrived broken",
        "description": "The mug was broken when the parcel arrived.",
        "priority": "high",
        "order_id": str(order.id),
    }
    llm = ScriptedLLM(
        tool_turn(("get_order_status", {"order_id": str(order.id)})),
        tool_turn(("create_support_ticket", args)),
        lambda request: text_turn(f"I've opened ticket #{json.loads(tool_results(request)[0]['content'])['ticket_id']}."),
    )
    result = run(db, alice, embedder, llm, "My mug arrived broken")

    assert [c.name for c in result.tool_calls] == ["get_order_status", "create_support_ticket"]
    assert alice.customer is not None
    ticket = db.scalars(select(SupportTicket).where(SupportTicket.customer_id == alice.customer.id)).one()
    assert ticket.priority == TicketPriority.HIGH
    assert ticket.description.startswith(f"Order #{order.id}: ")
    assert result.text == f"I've opened ticket #{ticket.id}."


def test_ticket_for_another_customers_order_is_refused(db: Session, embedder: Embedder, alice: User, bob: User) -> None:
    bobs_order = make_order(db, bob.customer)  # type: ignore[arg-type]
    args = {"subject": "Broken", "description": "Something arrived broken here.", "priority": "high", "order_id": str(bobs_order.id)}
    llm = ScriptedLLM(tool_turn(("create_support_ticket", args)), text_turn("I couldn't find that order."))
    result = run(db, alice, embedder, llm)
    assert result.tool_calls[0].status == "error"
    assert db.scalars(select(SupportTicket)).first() is None


def test_invalid_arguments_and_unknown_tools_are_reported_to_the_model(db: Session, embedder: Embedder, alice: User) -> None:
    llm = ScriptedLLM(
        tool_turn(("create_support_ticket", {"subject": "x", "description": "short", "priority": "high"}), ("drop_database", {})),
        text_turn("Could you tell me more?"),
    )
    result = run(db, alice, embedder, llm)
    assert [c.status for c in result.tool_calls] == ["error", "error"]
    contents = [r["content"] for r in results_of_round(llm, 1)]
    assert "Invalid arguments" in contents[0]
    assert "Unknown tool" in contents[1]


def test_knowledge_base_sources_are_numbered_and_cited(db: Session, embedder: Embedder, alice: User) -> None:
    ingest(db, embedder, "Return Policy.pdf", make_pdf(RETURNS_PDF_SECTIONS, title="Return Policy"))
    llm = ScriptedLLM(
        tool_turn(("search_knowledge_base", {"query": "how many days to return a product"})), text_turn("You have 30 days [S1].")
    )
    result = run(db, alice, embedder, llm)

    data = json.loads(results_of_round(llm, 1)[0]["content"])
    assert data["results"][0]["source"] == "S1"
    assert data["results"][0]["document"] == "Return Policy.pdf"
    assert len(result.sources) == 1 and result.sources[0].filename == "Return Policy.pdf"


def test_not_found_answer_has_no_sources(db: Session, embedder: Embedder, alice: User) -> None:
    from app.rag.rag_service import NOT_FOUND_MESSAGE

    ingest(db, embedder, "Return Policy.pdf", make_pdf(RETURNS_PDF_SECTIONS, title="Return Policy"))
    llm = ScriptedLLM(tool_turn(("search_knowledge_base", {"query": "return policy for gift cards"})), text_turn(NOT_FOUND_MESSAGE))
    assert run(db, alice, embedder, llm).sources == []


def test_tool_rounds_are_capped(db: Session, embedder: Embedder, alice: User) -> None:
    llm = ScriptedLLM(*[tool_turn(("get_customer_orders", {})) for _ in range(3)], text_turn("Here is what I found."))
    result = run(db, alice, embedder, llm)
    assert len(result.tool_calls) == 3
    assert llm.calls[-1]["tools"] is None  # the last round has no tools, so the model must answer
    assert result.text == "Here is what I found."


def test_refusal_gives_the_fallback_reply(db: Session, embedder: Embedder, alice: User) -> None:
    result = run(db, alice, embedder, ScriptedLLM("refuse"))
    assert result.text == FALLBACK_REPLY


def test_search_first_gives_the_model_the_documents_before_it_answers(db: Session, embedder: Embedder, alice: User) -> None:
    ingest(db, embedder, "Return Policy.pdf", make_pdf(RETURNS_PDF_SECTIONS, title="Return Policy"))
    events: list[dict[str, Any]] = []
    llm = ScriptedLLM(text_turn("how many days to return a product"), text_turn("Je hebt 30 dagen [S1]."))
    agent = SupportAgent(llm, SupportTools(db, alice, embedder), alice, search_first=True)
    result = agent.run([], "Hoeveel dagen heb ik om iets terug te sturen?", on_event=events.append)

    rewrite_call, answer_call = llm.calls
    assert "ENGLISH search query" in rewrite_call["system"]
    assert "Hoeveel dagen" in rewrite_call["messages"][0]["content"]
    assert result.tool_calls[0].name == "search_knowledge_base"
    assert result.tool_calls[0].arguments == {"query": "how many days to return a product"}
    assert "30 days" in answer_call["system"] and '"source": "S1"' in answer_call["system"]  # the documents reached the model
    assert [e["type"] for e in events][:2] == ["tool_start", "tool_end"]  # shown in the chat trace
    assert [s.filename for s in result.sources] == ["Return Policy.pdf"]


def test_search_first_tells_the_model_when_nothing_was_found(db: Session, embedder: Embedder, alice: User) -> None:
    ingest(db, embedder, "Return Policy.pdf", make_pdf(RETURNS_PDF_SECTIONS, title="Return Policy"))
    llm = ScriptedLLM(text_turn("painter of the Mona Lisa"), text_turn(NOT_FOUND))
    result = SupportAgent(llm, SupportTools(db, alice, embedder), alice, search_first=True).run([], "Who painted the Mona Lisa?")
    assert "found nothing relevant" in llm.calls[1]["system"]
    assert result.sources == []


def test_search_first_only_lists_sources_the_answer_cites(db: Session, embedder: Embedder, alice: User) -> None:
    ingest(db, embedder, "Return Policy.pdf", make_pdf(RETURNS_PDF_SECTIONS, title="Return Policy"))
    order = make_order(db, alice.customer)  # type: ignore[arg-type]
    llm = ScriptedLLM(
        text_turn("return a product"),
        tool_turn(("get_order_status", {"order_id": str(order.id)})),
        text_turn(f"Order #{order.id} has shipped."),
    )
    result = SupportAgent(llm, SupportTools(db, alice, embedder), alice, search_first=True).run([], f"Can I return order {order.id}?")
    # the agent's own lookups (order number in the message, knowledge base), then the model's own call
    assert [c.name for c in result.tool_calls] == ["get_order_status", "search_knowledge_base", "get_order_status"]
    assert result.sources == []  # no [S#] in the answer → no sources listed


def test_tools_reject_a_customer_id_from_the_model(db: Session, embedder: Embedder, alice: User, bob: User) -> None:
    llm = ScriptedLLM(tool_turn(("get_customer_orders", {"customer_id": bob.customer.id})), text_turn("Sorry."))  # type: ignore[union-attr]
    run(db, alice, embedder, llm)
    [sent] = results_of_round(llm, 1)
    assert sent["is_error"] is True and "customer_id" in sent["content"]


def test_search_first_looks_up_order_numbers_in_the_message(db: Session, embedder: Embedder, alice: User, bob: User) -> None:
    own = make_order(db, alice.customer)  # type: ignore[arg-type]
    other = make_order(db, bob.customer)  # type: ignore[arg-type]
    llm = ScriptedLLM(text_turn("order delivery time"), text_turn("Your order has shipped."))
    agent = SupportAgent(llm, SupportTools(db, alice, embedder), alice, search_first=True)
    result = agent.run([], f"Where are #{own.id} and {other.id}? Ordered on 2026-10-01.")

    assert [(c.name, c.arguments, c.status) for c in result.tool_calls[:2]] == [
        ("get_order_status", {"order_id": str(own.id)}, "ok"),
        ("get_order_status", {"order_id": str(other.id)}, "error"),  # Bob's order: not found for Alice
    ]
    system = llm.calls[1]["system"]
    assert "PO123456789" in system  # Alice's real order data reached the model
    assert system.count("PO123456789") == 1  # and nothing of Bob's


def test_order_numbers_are_recognised() -> None:
    from app.agents.support_agent import order_numbers

    assert order_numbers("Where is #10482? And 10482 again, and 10501") == ["10482", "10501"]
    assert order_numbers("I ordered 2 shirts in 2026 for 69.95, call 0612345678") == []


def test_search_products_tool_lists_sizes_in_stock(db: Session, embedder: Embedder, alice: User) -> None:
    from app.models import ProductCategory
    from tests.conftest import make_product, make_team

    team = make_team(db, "polder-united", "Polder United")
    make_product(
        db, "Polder United Home Shirt", "49.95", {"M": 0, "L": 3}, category=ProductCategory.HOME, team=team, compare_at_price="69.95"
    )
    tools = SupportTools(db, alice, embedder)

    found = json.loads(tools.execute("search_products", {"query": "Polder United home shirt"}).content)["results"]
    assert found[0]["product"] == "Polder United Home Shirt" and found[0]["sizes_in_stock"] == ["L"] and found[0]["was_eur"] == "69.95"
    in_m = tools.execute("search_products", {"query": "Polder United", "size": "m"})
    assert json.loads(in_m.content)["results"] == [] and in_m.summary == "No matching products"


def test_cancellation_is_only_offered_never_done_by_the_agent(db: Session, embedder: Embedder, alice: User, bob: User) -> None:
    from app.models import Order, OrderStatus

    open_order = make_order(db, alice.customer, status=OrderStatus.PROCESSING)  # type: ignore[arg-type]
    shipped = make_order(db, alice.customer, status=OrderStatus.SHIPPED)  # type: ignore[arg-type]
    bobs = make_order(db, bob.customer, status=OrderStatus.PROCESSING)  # type: ignore[arg-type]
    tools = SupportTools(db, alice, embedder)

    offered = tools.execute("request_order_cancellation", {"order_id": str(open_order.id)})
    assert not offered.is_error and json.loads(offered.content)["can_cancel"] is True
    assert db.get(Order, open_order.id).status == OrderStatus.PROCESSING  # type: ignore[union-attr]  # not cancelled
    assert tools.execute("request_order_cancellation", {"order_id": str(shipped.id)}).is_error
    assert "not found" in tools.execute("request_order_cancellation", {"order_id": str(bobs.id)}).content.lower()


def test_search_first_looks_up_a_mentioned_club_and_size(db: Session, embedder: Embedder, alice: User) -> None:
    from app.agents.support_agent import mentioned_size
    from app.models import ProductCategory
    from tests.conftest import make_product, make_team

    team = make_team(db, "polder-united", "Polder United")
    make_product(db, "Polder United Home Shirt", "69.95", {"M": 4}, category=ProductCategory.HOME, team=team)
    llm = ScriptedLLM(text_turn("polder united shirt"), text_turn("Yes, it's in stock in M."))
    result = SupportAgent(llm, SupportTools(db, alice, embedder), alice, search_first=True).run(
        [], "Hebben jullie het Polder shirt in maat m?"
    )

    assert ("search_products", {"query": "Polder United", "size": "M"}) in [(c.name, c.arguments) for c in result.tool_calls]
    assert "Polder United Home Shirt" in llm.calls[1]["system"]
    assert mentioned_size("I'm usually an XL") == "XL" and mentioned_size("I'm fine, thanks") is None


def test_search_products_filters_by_price_and_sale(db: Session, embedder: Embedder, alice: User) -> None:
    from app.models import ProductCategory
    from tests.conftest import make_product

    make_product(db, "Cheap Socks", "12.95")
    make_product(db, "Sale Shirt", "44.95", category=ProductCategory.HOME, compare_at_price="69.95")
    make_product(db, "Training Top", "39.95", category=ProductCategory.TRAINING)
    make_product(db, "Home Shirt", "69.95", category=ProductCategory.HOME)
    tools = SupportTools(db, alice, embedder)

    def names(**args: object) -> list[str]:
        return [r["product"] for r in json.loads(tools.execute("search_products", args).content)["results"]]

    assert sorted(names(min_price=40, max_price=50)) == ["Sale Shirt"]
    assert sorted(names(max_price=40)) == ["Cheap Socks", "Training Top"]
    assert names(on_sale=True) == ["Sale Shirt"]
    assert sorted(names(category="home")) == ["Home Shirt", "Sale Shirt"]
    assert json.loads(tools.execute("search_products", {}).content)["total_matching"] == 4  # no filters: browse


def test_a_price_question_gets_products_even_when_the_knowledge_base_has_nothing(db: Session, embedder: Embedder, alice: User) -> None:
    """Regression: "shirts tussen 40-50 euro" was answered with "not found" although such shirts exist."""
    from app.models import ProductCategory
    from tests.conftest import make_product

    make_product(db, "Polder United Home Shirt", "49.95", category=ProductCategory.HOME, compare_at_price="69.95")
    llm = ScriptedLLM(text_turn("shirts between 40 and 50 euro"), text_turn("Yes: the Polder United Home Shirt costs EUR 49.95."))
    agent = SupportAgent(llm, SupportTools(db, alice, embedder), alice, search_first=True)
    result = agent.run([], "Hebben jullie shirts tussen 40-50 euro?")

    search = next(c for c in result.tool_calls if c.name == "search_products")
    assert search.arguments == {"min_price": 40, "max_price": 50} and search.status == "ok"
    system = llm.calls[1]["system"]
    assert "Polder United Home Shirt" in system and "These products exist" in system
    assert "found nothing relevant" not in system  # no "not found" instruction when products were found
    assert system.rindex("These products exist") > system.rindex("Knowledge-base") if "Knowledge-base" in system else True
