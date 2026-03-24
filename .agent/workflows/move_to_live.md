---
description: move a finished feature from test.localhost to live.localhost
---

# Move to Live Workflow

Use this workflow after finishing and testing a feature on `test.localhost`.
It exports fixtures, commits code to Git, and migrates `live.localhost`.

// turbo-all

## Steps

1. Stop `bench start` if it is running (Ctrl+C in the bench start terminal).

2. Export fixtures from the test site:
```bash
cd /Users/accounting-macmini/Desktop/Tourism_Local/tourism-bench
bench --site test.localhost export-fixtures
```

3. Commit all changes to git:
```bash
cd /Users/accounting-macmini/Desktop/Tourism_Local/tourism-bench/apps/tourism_app
git add -A
git commit -m "feat: <describe your feature here>"
```

4. Migrate the live site to apply new code and fixtures:
```bash
cd /Users/accounting-macmini/Desktop/Tourism_Local/tourism-bench
bench --site live.localhost migrate
```

5. Restart the server:
```bash
cd /Users/accounting-macmini/Desktop/Tourism_Local/tourism-bench
bench start
```

6. Open http://live.localhost:8000 and verify the feature is working correctly.

> **Tip**: You can also run the one-liner helper script instead of steps 2–4:
> ```bash
> cd /Users/accounting-macmini/Desktop/Tourism_Local/tourism-bench
> ./move_to_live.sh "feat: your feature description"
> ```
