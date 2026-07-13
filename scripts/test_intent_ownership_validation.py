from __future__ import annotations

import validate_system_tts_ivr as target


def main() -> None:
    bad_scene = [{"nodeList": [{"name": "开场白", "intentList": [{"34642": "node-next"}], "interruptedIntentList": ["34642"]}]}]
    bad_front = [{
        "nodeList": [{"name": "开场白", "intentList": [{"value": "34642", "label": "普通拒绝", "digitSequence": ""}]}],
        "graph": {"cells": [{"id": "node-opening", "data": {"customData": {"name": "开场白", "intentList": [{"value": "34642", "label": "普通拒绝", "digitSequence": ""}]}}}]},
    }]
    issues = target.intent_ownership_issues(bad_scene, bad_front, {"34627": "普通拒绝"}, "fixture")
    assert issues and all("34642" in issue for issue in issues)

    reserved_scene = [{"nodeList": [{"intentList": [{"-2": ""}, {"-1": "node-next"}]}]}]
    reserved_front = [{"nodeList": [{"intentList": [{"value": "-2", "label": "知识库", "digitSequence": ""}, {"value": "-1", "label": "兜底", "digitSequence": ""}]}], "graph": {"cells": []}}]
    assert not target.intent_ownership_issues(reserved_scene, reserved_front, {}, "reserved")
    print("TALKTRACK_MASTER_INTENT_OWNERSHIP_TEST=PASS")


if __name__ == "__main__":
    main()
