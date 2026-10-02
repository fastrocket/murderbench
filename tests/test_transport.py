from io import BytesIO
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import Mock, patch
import urllib.error
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'benchmark'))
import study

class TransportTests(unittest.TestCase):
    def test_malformed_received_body_preserved(self):
        with patch.object(study.urllib.request,'urlopen',return_value=BytesIO(b'not-json')):
            result=study.fetch('/chat/completions','test-key',{'model':'test'})
        self.assertEqual(result,{'response_parse_error':True,'raw_response':'not-json'})
        self.assertNotIn('test-key',str(result))

    def test_http_error_body_preserved(self):
        error=urllib.error.HTTPError('https://example.test',503,'test',None,BytesIO(b'{"error":"test unavailable"}'))
        with patch.object(study.urllib.request,'urlopen',side_effect=error):
            result=study.fetch('/chat/completions','test-key',{'model':'test'})
        self.assertEqual(result,{'http_status':503,'error_body':'{"error":"test unavailable"}'})

    def test_waiting_admission_is_rejected_after_stop_publication(self):
        lock=threading.Lock();stop=threading.Event();store=Mock();outcomes=[]
        lock.acquire()
        worker=threading.Thread(target=lambda:outcomes.append(study.admit(store,stop,lock,'test',{})))
        worker.start()
        stop.set();lock.release();worker.join(timeout=5)
        self.assertFalse(worker.is_alive())
        self.assertEqual(outcomes,[False]);store.reserve.assert_not_called()
