# Driver: Creates a minimal Aim run so the search endpoint has data to query.
"""Create a minimal Aim run so the search endpoint has data to query."""
from aim import Run

run = Run()
run["dummy"] = 1
run.track(1.0, name="metric")
run.close()
print("Dummy run created.")
