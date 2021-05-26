#! /bin/sh
echo "DELETING BVT-TEST"
mongo <<EOF
use bvt-test
db.dropDatabase()
quit()
exit