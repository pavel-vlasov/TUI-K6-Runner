from textual.containers import Horizontal, ScrollableContainer
from textual.widgets import Input, Label


class StageMixin:
    def get_spike_stages(self):
        stages = self.full_config.get("k6", {}).get("spikeStages", [])
        if not isinstance(stages, list) or not stages:
            return [{"duration": "30s", "target": 10}]
        normalized = []
        for stage in stages:
            if not isinstance(stage, dict):
                continue
            normalized.append(
                {
                    "duration": stage.get("duration", ""),
                    "target": stage.get("target", ""),
                }
            )
        return normalized or [{"duration": "30s", "target": 10}]

    def get_ramping_arrival_stages(self):
        stages = self.full_config.get("k6", {}).get("rampingArrivalStages", [])
        if not isinstance(stages, list) or not stages:
            return [{"duration": "30s", "target": 10}]
        normalized = []
        for stage in stages:
            if not isinstance(stage, dict):
                continue
            normalized.append(
                {
                    "duration": stage.get("duration", ""),
                    "target": stage.get("target", ""),
                }
            )
        return normalized or [{"duration": "30s", "target": 10}]

    def build_spike_stage_row(self, index: int, stage: dict) -> Horizontal:
        return Horizontal(
            Label(f"stage {index + 1}:", classes="field-label"),
            Input(
                str(stage.get("duration", "")),
                id=f"input___k6__spikeStages__{index}__duration",
                placeholder="duration (e.g. 30s)",
            ),
            Input(
                str(stage.get("target", "")),
                id=f"input___k6__spikeStages__{index}__target",
                placeholder="target VUs",
            ),
            classes="field-row spike-stage-row",
            id=f"spike_stage_row_{index}",
        )

    def build_arrival_stage_row(self, index: int, stage: dict) -> Horizontal:
        return Horizontal(
            Label(f"stage {index + 1}:", classes="field-label"),
            Input(
                str(stage.get("duration", "")),
                id=f"input___k6__rampingArrivalStages__{index}__duration",
                placeholder="duration (e.g. 30s)",
            ),
            Input(
                str(stage.get("target", "")),
                id=f"input___k6__rampingArrivalStages__{index}__target",
                placeholder="target rate",
            ),
            classes="field-row spike-stage-row",
            id=f"arrival_stage_row_{index}",
        )

    def add_spike_stage(self):
        container = self.query_one("#spike_stages_container", ScrollableContainer)
        stage_idx = len(container.children)
        row = self.build_spike_stage_row(stage_idx, {"duration": "", "target": ""})
        container.mount(row)

    def remove_last_spike_stage(self):
        container = self.query_one("#spike_stages_container", ScrollableContainer)
        if len(container.children) <= 1:
            return
        list(container.children)[-1].remove()

    def add_arrival_stage(self):
        container = self.query_one("#arrival_stages_container", ScrollableContainer)
        stage_idx = len(container.children)
        row = self.build_arrival_stage_row(stage_idx, {"duration": "", "target": ""})
        container.mount(row)

    def remove_last_arrival_stage(self):
        container = self.query_one("#arrival_stages_container", ScrollableContainer)
        if len(container.children) <= 1:
            return
        list(container.children)[-1].remove()
