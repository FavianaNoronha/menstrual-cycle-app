import json
from datetime import date, timedelta

from helpers import record_from_lengths

from cycle_engine import (
    FlowLog,
    Impact,
    PainLocation,
    PainLog,
    Product,
    ProductUse,
    Saturation,
    SleepLog,
    SymptomLog,
    Treatment,
    record_from_data,
    record_to_data,
)


def _full_record():
    rec = record_from_lengths([28, 30, 27], age=33)
    d = rec.periods[1].start
    rec.flow.append(FlowLog(d, [ProductUse(Product.PAD, Saturation.FULL), ProductUse(Product.CUP, cup_ml=30)], 1, 1, 1, "heavy"))
    rec.symptoms.append(SymptomLog(d, {"mood_low": 5}, {"sweet", "salty"}))
    rec.pain.append(
        PainLog(d, 8, {PainLocation.LOWER_BACK, PainLocation.BOWEL}, True, False, True, False, True,
                duration_minutes=120, nausea_vomiting=True, impacts={Impact.WORK, Impact.SLEEP})
    )
    rec.sleep.append(SleepLog(d, 5.5))
    rec.treatments.append(Treatment("Medicine", d + timedelta(days=3), True, side_effects=True))
    rec.profile.pregnancy_possible = False
    rec.soaking_hourly_hours = 2
    return rec


def test_round_trip_is_lossless_and_json_safe():
    rec = _full_record()
    data = record_to_data(rec)
    restored = record_from_data(json.loads(json.dumps(data)))  # must survive real JSON
    assert restored == rec
    assert record_to_data(restored) == data


def test_output_is_stable_for_sets():
    a = record_to_data(_full_record())
    b = record_to_data(_full_record())
    assert json.dumps(a) == json.dumps(b)


def test_old_data_without_new_fields_still_loads():
    data = record_to_data(record_from_lengths([28, 28]))
    for key in ("sleep", "treatments"):
        data.pop(key)
    assert record_from_data(data).sleep == []
