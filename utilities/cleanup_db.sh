#! /bin/sh
echo "DELETING ALL"

mongo <<EOF
use bvt-test
db.dropDatabase()
use bvt
db.dropDatabase()
quit()
exit