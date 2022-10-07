#!/bin/bash --login

set +euo pipefail
conda activate kilroy-face-twitter
set -euo pipefail

exec "$@"
