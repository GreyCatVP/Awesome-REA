"""Catalog identity remains the same in visible about pages and the agent navigation index."""
from html.parser import HTMLParser
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build_discovery_pages import build_discovery_pages
from build_home import COPY


class AboutIdentity(HTMLParser):
    def __init__(self, content):
        super().__init__(convert_charrefs=True)
        self.in_intro = False
        self.in_paragraph = False
        self.in_schema = False
        self.intro = ''
        self.schema_text = ''
        self.graphs = []
        self.canonicals = []
        self.feed(content)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'section' and 'collection-intro' in attrs.get('class', '').split():
            self.in_intro = True
        if tag == 'p' and self.in_intro:
            self.in_paragraph = not attrs.get('class')
        if tag == 'link' and attrs.get('rel') == 'canonical':
            self.canonicals.append(attrs['href'])
        if tag == 'script' and attrs.get('type') == 'application/ld+json':
            self.in_schema = True
            self.schema_text = ''

    def handle_endtag(self, tag):
        if tag == 'section':
            self.in_intro = False
        if tag == 'p':
            self.in_paragraph = False
        if tag == 'script' and self.in_schema:
            self.graphs.append(json.loads(self.schema_text))
            self.in_schema = False

    def handle_data(self, data):
        if self.in_paragraph:
            self.intro += data
        if self.in_schema:
            self.schema_text += data


class CatalogDefinitionTests(unittest.TestCase):
    def test_about_visible_and_structured_identity_matches_the_catalog_homepage(self):
        with TemporaryDirectory() as directory:
            output = Path(directory)
            build_discovery_pages(output, {'resources': [], 'meta': {}}, None)
            for language, prefix, readme in (('en', '', 'README.md'), ('zh', '/zh', 'README.zh-CN.md')):
                with self.subTest(language=language):
                    document = AboutIdentity((output / (prefix.lstrip('/') + '/about/index.html').lstrip('/')).read_text())
                    definition = (ROOT / readme).read_text().split('\n\n', 2)[1]
                    self.assertEqual(document.intro, definition)
                    self.assertEqual(document.intro, COPY[language]['lede'])
                    about = next(node for graph in document.graphs for node in graph.get('@graph', [])
                                 if node.get('@type') == 'AboutPage')
                    self.assertEqual(about['description'], document.intro)
                    self.assertEqual(about['about'], {'@id': 'https://awesomerea.org/#website'})
                    self.assertEqual(document.canonicals, ['https://awesomerea.org' + prefix + '/about/'])

    def test_agent_index_opens_with_the_same_identity_and_keeps_source_links(self):
        with TemporaryDirectory() as directory:
            output = Path(directory)
            build_discovery_pages(output, {'resources': [], 'meta': {}}, None)
            index = (output / 'llms.txt').read_text()
            summary = index.split('\n\n', 2)[1]
            self.assertEqual(summary, '> ' + COPY['en']['lede'])
            self.assertIn('[Public source repository](https://github.com/reacher-z/Awesome-REA)', index)
            self.assertIn('[About and provenance](https://awesomerea.org/about/)', index)
            self.assertIn('[关于与来源](https://awesomerea.org/zh/about/)', index)


if __name__ == '__main__':
    unittest.main()
