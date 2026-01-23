import re,sys,os
p='logs/chat_page_dom.log'
if not os.path.exists(p):
    print('no chat_page_dom.log')
    sys.exit(0)
pat=re.compile(r'IMMEDIATE_PROMOTED_BY_META_PRECHECK|IMMEDIATE_PROMOTED_BY_META|IMMEDIATE_PRECHECK_SKIPPED|IMMEDIATE_DIAG|IMMEDIATE_CALL_ATTEMPT|IMMEDIATE_SUCCESS|IMMEDIATE_RATE_LIMIT|IMMEDIATE_NO_PAGE|IMMEDIATE_CALL_FAIL|\bSUCCESS message_id=')
found=False
with open(p,'r',encoding='utf-8',errors='ignore') as f:
    for line in f:
        if pat.search(line):
            print(line.rstrip())
            found=True
if not found:
    print('NO_MATCHES')
