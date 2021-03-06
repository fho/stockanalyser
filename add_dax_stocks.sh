#!/usr/bin/env bash

set -u

isins=(DE000A1EWWW0 DE000BASF111 DE000BAY0017 DE0005200000 DE000A1ML7J1\
       DE0005190003 DE0005439004 DE0007100000 DE0005552004 DE0005557508\
       DE000ENAG999 DE0005785604 DE0005785802 DE0006047004 DE0006048432\
       DE0006231004 DE0006483001 DE0008232125 DE0006599905 DE000PSM7770\
       DE0007037129 DE0007164600 DE0007236101 DE0007500001 DE0007664039)

# the finance stocks are not added, rules to handle finance stocks correctly are not
# implemented yet
#	DE000CBK1001
#	DE0008430026
#	DE0005140008
#	DE0005810055
#       DE0008404005 


for i in "${isins[@]}"; do
	./analyser -d add "$i"
done
