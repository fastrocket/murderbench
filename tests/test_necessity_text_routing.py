import unittest
from benchmark.necessity_text_routing import text_only_payload
from benchmark.necessity_structural_native import payload_for
from benchmark.necessity_events import TOOLS

class TextRoutingTests(unittest.TestCase):
    def test_only_image_price_filter_changes(self):
        route={"model":"test/model","provider":"test"}
        messages=[{"role":"user","content":"Call wait."}]
        old=payload_for(route,messages,TOOLS)
        new=text_only_payload(route,messages,TOOLS)
        old["provider"]["max_price"].pop("image")
        self.assertEqual(old,new)
        self.assertEqual(new["provider"]["data_collection"],"deny")

    def test_non_text_content_rejected_before_request(self):
        for content in ([{"type":"image_url","image_url":{"url":"https://example.invalid/x.png"}}],{},12,None):
            with self.assertRaises(ValueError):
                text_only_payload({"model":"test/model","provider":"test"},[{"role":"user","content":content}],TOOLS)
