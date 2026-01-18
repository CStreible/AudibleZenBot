import zipfile, sys
from core.logger import get_logger

logger = get_logger('inspect_pyz')

p='build/AudibleZenBot/PYZ-00.pyz'
try:
    with zipfile.ZipFile(p) as z:
        names=[n for n in z.namelist() if 'connections_page' in n.lower()]
        for n in names:
            logger.info(n)
        logger.info('--- total entries: %d', len(z.namelist()))
except Exception as e:
    logger.exception(f'ERROR: {e}')
    sys.exit(1)
