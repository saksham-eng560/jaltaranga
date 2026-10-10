# Jaltaranga: follow-up tasks for the next agent

Repo `saksham-eng560/jaltaranga`. Do your work on branch `feature/saksham`, starting from the current `main`.
When everything under **Merge rule** holds, merge `feature/saksham` into `main` and push.

## Current state (2026-10-10)

- `main` contains all four feature branches (saksham, shivansh, arjav, vaibhav), merged and pushed (`baf8460`).
- AWS stack `jt-demo` is deployed in `ap-south-1`, account `410133710130`.
  - API: `https://qu36c9519d.execute-api.ap-south-1.amazonaws.com`
  - Bucket: `jt-demo-data-410133710130`
  - SNS topic: `jt-demo-dispatch` (email subscription confirmed)
  - Tables: `jt-demo-{colonies,dispatches,reports,scenario-state,shelters}`
- The data in the bucket is the synthetic **dev world** (`routing/jt_routing/devworld.py`), not real pipeline output.
- When the stack was deployed, Bedrock refused every call with `AccessDeniedException ... account is currently being verified`.
  AWS has since emailed that verification is complete, so Bedrock should now work. It has not been re-tested.
- Deployed with `BedrockRegion=us-east-1`, `BedrockModelId=us.amazon.nova-micro-v1:0` (the template defaults, not from a probe).
- Full record: `docs/workstreams/saksham/STATUS.md`, section "Deployed".

## Environment setup

- AWS keys are in the environment (`AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`, region `ap-south-1`).
  Check them with boto3 `sts.get_caller_identity()`.
- There is no `aws` or `sam` binary and Docker is down. Install both in a **separate venv** so the venv does not shadow the
  system Python (that broke `make demo-local` last time):
  ```bash
  python3 -m venv /opt/samvenv && /opt/samvenv/bin/pip install aws-sam-cli awscli boto3
  export PATH=$PATH:/opt/samvenv/bin      # append, don't prepend
  ```
- System Python needs: `pip install boto3 -r routing/requirements-offline.txt`
- For the ML tests also: `pip install scipy pandas pyarrow scikit-learn scikit-image shapely rasterio pyyaml`
- Build with `cd infra && sam build` (no `--use-container`; `/usr/bin/python3.12` exists).

## Tasks, in order

### 1. Fix the red CI on `feature/saksham`
A GitHub Actions run of "routing-alerts (Saksham) / test" failed on `feature/saksham` at about 06:00 UTC on 2026-10-10, before the merges.
Read the job logs, find the root cause, and fix it. Never skip or disable a test. Also check that CI is green on `main`.

### 2. Run the ML tests in CI
`ml/tests` (7 tests) is not in `pytest.ini` `testpaths` or in CI. They pass when run with:
`PYTHONPATH=ml:shared/py python3 -m pytest -q ml/tests`.
Add them to CI with their dependencies. A separate job is fine, so the routing/alerts job stays light.

### 3. Remove generated files from the ml commit
`ml/jt_ml.egg-info/` and `ml/out/` are committed. First check whether anything reads `ml/out`. If nothing does,
`git rm -r --cached` both and add them to `.gitignore`. Leave `ml/uv.lock` in place.

### 4. Make publishing self-sufficient
A fresh deploy needed three manual steps. Add them to the Makefiles:
- Upload `scenarios/<id>/manifest.json`, `gauges.json` and `static/{colonies,shelters}.geojson`. Without the manifest,
  `GET /scenarios/{id}/*` returns 404 `scenario_not_found`. These are pipeline-owned files, so upload only when
  the file exists locally.
- Seed the `jt-<env>-shelters` DynamoDB table from `static/shelters.geojson`, validating each feature with
  `jt_shared.models.Shelter`. Make the seed idempotent, and do not overwrite `occupied`/`free_beds` on rows that already exist.

### 5. Bedrock and deploy (AWS)
```bash
make -C alerts probe          # must now succeed; note JT_BEDROCK_REGION / JT_BEDROCK_MODEL_ID
```
- If the probe picks a different profile, redeploy:
  ```bash
  cd infra && sam build && sam deploy --stack-name jt-demo --region ap-south-1 --resolve-s3 \
    --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND --no-confirm-changeset \
    --parameter-overrides Env=demo BedrockRegion=<probe> BedrockModelId=<probe> \
    DispatchEmail=sakshamverma56000@gmail.com BudgetEmail=sakshamverma56000@gmail.com
  ```
- `make -C routing demo-local`, then `make -C routing publish` and `make -C alerts publish` with `BUCKET=jt-demo-data-410133710130`.
  The predraft cards should now show `"bedrock": true` and fewer fallbacks.
- Run `make -C alerts halluc-live N=20` and commit the recordings in `alerts/tests/recorded/`. It must report
  0 untraceable tokens; if it doesn't, stop and report.
- Check Polly: approving a dispatch must return an `audio_url`. It returned none last time. If it still fails, check the
  IAM policy for `polly:SynthesizeSpeech` in `ap-south-1`.
- Each approve sends a **real email** to sakshamverma56000@gmail.com. Approve at most one dispatch for the test.
- Stay within the USD 10 budget. Do not create resources outside the stack.

### 6. Tell Vaibhav about the key format change
In the merge, Vaibhav's `jt_shared.naming` helpers (`forecast_key`, `depth_*_key`) now return **raw** `+05:30`
timestamps. They used to return percent-encoded `%2B05%3A30`, but raw keys are the contract and what `s3_key` uses. Use `url_key()` only for
HTTP paths. Check `ml/` and `ml/lambda` for any code that builds keys itself or assumes the encoded form.
Fix it if so, then add a note to `docs/workstreams/vaibhav/` (not a GitHub comment).

### 7. Update STATUS.md
Rewrite the "Deployed" section of `docs/workstreams/saksham/STATUS.md` with what actually ran, the probe result
and the remaining gaps. Report failures as failures.

## Merge rule

Merge `feature/saksham` into `main` (a merge commit, no force-push, no history rewrite) **only if all of these hold**:
1. `pytest` (root, 136+ tests) and the `ml/tests` command both pass locally.
2. CI is green on the `feature/saksham` head.
3. `git merge origin/main` into `feature/saksham` produced no conflicts, or only conflicts you resolved without
   losing either side's behaviour. Re-run the tests after resolving.
4. `make -C routing demo-local` still passes its invariants (it exits non-zero on a safety violation).
5. No secrets, `.aws-sam/`, `data/`, or generated outputs in the diff.

If any of these fails, do not merge. Push the branch and report exactly what is blocking.
If both sides changed the same logic and either resolution would lose behaviour, stop and ask.

## Don'ts
- Don't push directly to other people's branches (`feature/vaibhav`, `feature/shivansh`, `feature/arjav`).
- Don't open PRs or post GitHub comments unless asked.
- Don't put model identifiers in commits or docs.
