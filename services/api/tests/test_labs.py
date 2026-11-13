import pytest
from pydantic import ValidationError

from labs import (
    EquipmentCreate,
    EquipmentStatusUpdate,
    ExperimentCreate,
    ExperimentEventCreate,
    ProjectCreate,
    ProjectStatusUpdate,
)


def test_project_create_normalises_title_and_deduplicates_objectives():
    project = ProjectCreate(
        title="  ORIOM7   accelerator research ",
        discipline="semiconductors",
        objectives=["Benchmark memory bandwidth", " Benchmark memory bandwidth "],
    )
    assert project.title == "ORIOM7 accelerator research"
    assert project.objectives == ["Benchmark memory bandwidth"]


def test_project_rejects_unknown_fields_and_invalid_discipline():
    with pytest.raises(ValidationError):
        ProjectCreate(title="Research project", owner_subject="attacker")
    with pytest.raises(ValidationError):
        ProjectCreate(title="Research project", discipline="classified")


def test_experiment_configuration_is_bounded_and_json_safe():
    experiment = ExperimentCreate(
        title="FPGA memory controller prototype",
        configuration={"clock_mhz": 200, "board": "prototype-a"},
    )
    assert experiment.configuration["clock_mhz"] == 200

    with pytest.raises(ValidationError):
        ExperimentCreate(title="FPGA experiment", configuration={"payload": "x" * 17000})

    with pytest.raises(ValidationError):
        ExperimentCreate(title="FPGA experiment", configuration={"not_json": object()})


def test_experiment_event_is_typed_bounded_and_rejects_extra_fields():
    event = ExperimentEventCreate(
        event_type="measurement",
        summary="Recorded memory throughput",
        data={"throughput_gbps": 128.5, "unit": "GB/s"},
    )
    assert event.event_type == "measurement"

    with pytest.raises(ValidationError):
        ExperimentEventCreate(
            event_type="measurement",
            summary="Recorded result",
            actor="someone-else",
        )

    with pytest.raises(ValidationError):
        ExperimentEventCreate(
            event_type="measurement",
            summary="Recorded result",
            data={"large": "x" * 17000},
        )


def test_equipment_registry_validates_fields_and_metadata_size():
    equipment = EquipmentCreate(
        name="Oscilloscope 01",
        category="electronics",
        manufacturer="Example Instruments",
        asset_tag="ORIOM7-ELEC-001",
    )
    assert equipment.asset_tag == "ORIOM7-ELEC-001"

    with pytest.raises(ValidationError):
        EquipmentCreate(name=" ", category="electronics")

    with pytest.raises(ValidationError):
        EquipmentCreate(name="Oscilloscope", category="electronics", metadata={"large": "x" * 17000})


def test_status_models_reject_unknown_values_and_extra_fields():
    assert ProjectStatusUpdate(status="active").status == "active"
    assert EquipmentStatusUpdate(status="maintenance").status == "maintenance"

    with pytest.raises(ValidationError):
        ProjectStatusUpdate(status="running")

    with pytest.raises(ValidationError):
        EquipmentStatusUpdate(status="working", owner_subject="attacker")


def test_notebook_entry_validates_content_and_rejects_client_identity():
    from labs import NotebookEntryCreate

    entry = NotebookEntryCreate(
        entry_type="measurement",
        title="GPU memory bandwidth result",
        content="Measured 812 GB/s under the documented test conditions.",
        metadata={"unit": "GB/s", "run": 3},
    )
    assert entry.entry_type == "measurement"
    assert entry.content.startswith("Measured")

    with pytest.raises(ValidationError):
        NotebookEntryCreate(
            entry_type="note", title="A valid title", content="Valid content",
            owner_subject="attacker",
        )

    with pytest.raises(ValidationError):
        NotebookEntryCreate(entry_type="note", title="  ", content="   ")

    with pytest.raises(ValidationError):
        NotebookEntryCreate(
            entry_type="note", title="A valid title", content="Valid content",
            metadata={"large": "x" * 17000},
        )


def test_notebook_entry_rejects_unknown_entry_type_and_oversized_content():
    from labs import NotebookEntryCreate

    with pytest.raises(ValidationError):
        NotebookEntryCreate(entry_type="chat", title="Valid title", content="Body")

    with pytest.raises(ValidationError):
        NotebookEntryCreate(
            entry_type="note", title="Valid title", content="x" * 20001,
        )
