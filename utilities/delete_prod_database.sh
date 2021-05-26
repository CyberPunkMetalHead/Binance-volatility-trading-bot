#! /bin/sh
echo "DELETING BVT"
mongo <<EOF
use bvt
db.dropDatabase()
quit()
exit