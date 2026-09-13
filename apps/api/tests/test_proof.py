from __future__ import annotations

from app.contracts import ExecutionStatus
from app.model.nemotron import NemotronModelService
from app.model.router import ModelRouter
from app.runtime.proof import ProofPathService
from app.settings import Settings
from tests.conftest import (
    FakeSandbox,
    FakeTokenFactoryClient,
    make_command_result,
)


def _settings() -> Settings:
    return Settings(
        nebius_api_key="k",
        nebius_ai_project="p",
        nemotron_model_nano="model-nano",
        nemotron_model_super="model-super",
        nemotron_model_ultra="model-ultra",
    )


def _build_proof(
    *,
    content: str = "INFRA_OK",
    command_exit_code: int = 0,
) -> tuple[Settings, ProofPathService, FakeTokenFactoryClient, FakeSandbox]:
    settings = _settings()
    client = FakeTokenFactoryClient(content=content, model=settings.nemotron_model_nano)
    service = NemotronModelService(
        client=client, router=ModelRouter(settings=settings), settings=settings
    )
    sandbox = FakeSandbox()
    if command_exit_code != 0:
        sandbox.command_results.append(
            make_command_result(
                exit_code=command_exit_code,
                stdout="",
                stderr="boom",
                command="echo INFRA_OK && python3 --version",
            )
        )
    proof = ProofPathService(settings=settings, model_service=service, sandbox=sandbox)
    return settings, proof, client, sandbox


async def test_proof_is_machine_verifiable_when_all_evidence_is_positive() -> None:
    settings, proof, client, sandbox = _build_proof()
    result = await proof.execute()
    assert result.machine_verifiable is True
    assert result.execution_authoritative is True
    assert result.model_participated is True
    assert result.routing.selected_model == settings.nemotron_model_nano
    assert result.model_response.content == "INFRA_OK"
    assert result.sandbox.base_image == settings.sandbox_base_image
    assert sandbox.last_created_base_image == settings.sandbox_base_image
    assert client.last_request is not None
    assert result.request_id == client.last_request.request_id


async def test_proof_not_verifiable_when_command_fails() -> None:
    _, proof, _, _ = _build_proof(command_exit_code=1)
    result = await proof.execute()
    assert result.execution_authoritative is False
    assert result.machine_verifiable is False
    assert result.command_result.status is ExecutionStatus.FAILED
    assert result.command_result.exit_code == 1
    assert result.model_participated is True


async def test_proof_not_verifiable_when_model_returns_no_content() -> None:
    _, proof, _, _ = _build_proof(content="")
    result = await proof.execute()
    assert result.model_participated is False
    assert result.machine_verifiable is False
    assert result.execution_authoritative is True
