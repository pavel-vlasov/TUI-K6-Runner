from app_mixins.stage_mixin import StageMixin


class DummyChild:
    def __init__(self):
        self.removed = False

    def remove(self):
        self.removed = True


class DummyContainer:
    def __init__(self, count=1):
        self.children = [DummyChild() for _ in range(count)]
        self.mounted = []

    def mount(self, row):
        self.mounted.append(row)
        self.children.append(DummyChild())


class DummyStageUI(StageMixin):
    def __init__(self, full_config=None, spike_count=1, arrival_count=1):
        self.full_config = full_config or {}
        self.spike_container = DummyContainer(spike_count)
        self.arrival_container = DummyContainer(arrival_count)

    def query_one(self, selector, _widget_type):
        if selector == "#spike_stages_container":
            return self.spike_container
        if selector == "#arrival_stages_container":
            return self.arrival_container
        raise KeyError(selector)


def test_stage_defaults_and_normalization():
    ui = DummyStageUI(full_config={"k6": {"spikeStages": ["bad", {"duration": "5s", "target": 2}]}})

    spike = ui.get_spike_stages()
    assert spike == [{"duration": "5s", "target": 2}]

    empty = DummyStageUI(full_config={"k6": {"spikeStages": []}})
    assert empty.get_spike_stages() == [{"duration": "30s", "target": 10}]


def test_add_and_remove_spike_stage():
    ui = DummyStageUI(spike_count=2)

    ui.add_spike_stage()
    assert ui.spike_container.mounted

    removed = ui.remove_last_spike_stage()
    assert removed is True
    assert ui.spike_container.children[-1].removed is True


def test_remove_last_spike_stage_does_not_remove_single_row():
    ui = DummyStageUI(spike_count=1)
    removed = ui.remove_last_spike_stage()
    assert removed is False
    assert len(ui.spike_container.children) == 1
    assert all(not child.removed for child in ui.spike_container.children)


def test_add_and_remove_arrival_stage():
    ui = DummyStageUI(arrival_count=2)

    ui.add_arrival_stage()
    assert ui.arrival_container.mounted

    removed = ui.remove_last_arrival_stage()
    assert removed is True
    assert ui.arrival_container.children[-1].removed is True


def test_remove_last_arrival_stage_does_not_remove_single_row():
    ui = DummyStageUI(arrival_count=1)
    removed = ui.remove_last_arrival_stage()
    assert removed is False
    assert len(ui.arrival_container.children) == 1
    assert all(not child.removed for child in ui.arrival_container.children)
