
import io
import os
import sys
import json
import yaml
from random import choice
from string import ascii_uppercase
from msgpack import pack, Unpacker
from gatenlp.document import Document
from gatenlp.annotation_set import AnnotationSet
from gatenlp.annotation import Annotation
from gatenlp.changelog import ChangeLog
from gzip import open as gopen, compress, decompress
from pathlib import Path
from urllib.parse import ParseResult
import requests
from bs4 import BeautifulSoup
import bs4

# TODO: when loading from a URL, allow for deciding on the format based on the mime type!
# So if we do not have the format, we should get the header for the file, check the mime type and see
# if  we have a loder registered for that and then let the loader do the rest of the work. This may
# need loaders to be able to use an already open stream. 


def is_url(ext):
    """
    Returns True, urlstring if ext should be interpreted as a (HTTP(s)) URL, otherwise false, pathstring
    If ext is None, returns None, None.

    :param ext: something that represents an external resource: string, url parse, pathlib path object ...
    :return: True, usrlstring or False, pathstring
    """
    if ext is None:
        return None, None
    if isinstance(ext, str):
        if ext.startswith("http://") or ext.startswith("https://"):
            return True, ext
        else:
            return False, ext
    elif isinstance(ext, Path):
        return False, str(ext)
    elif isinstance(ext, ParseResult):
        return True, ext.geturl()
    else:
        raise Exception(f"Odd type: {ext}")



def get_str_from_url(url, encoding=None):
    """
    Read a string from the URL.

    :param url: some URL
    :param encoding: override the encoding that would have determined automatically
    :return: the string
    """
    req = requests.get(url)
    if encoding is not None:
        req.encoding = encoding
    return req.text

def get_bytes_from_url(url):
    """
    Read bytes from url.

    :param url: the URL
    :return: the bytes
    """
    req = requests.get(url)
    return req.content


class JsonSerializer:

    @staticmethod
    def save(clazz, inst, to_ext=None, to_mem=None, offset_type=None, offset_mapper=None, gzip=False, **kwargs):
        d = inst.to_dict(offset_type=offset_type, offset_mapper=offset_mapper, **kwargs)
        if to_mem:
            if gzip:
                compress(json.dumps(d).encode("UTF-8"))
            else:
                return json.dumps(d)
        else:
            if gzip:
                with gopen(to_ext, "wt") as outfp:
                    json.dump(d, outfp)
            else:
                with open(to_ext, "wt") as outfp:
                    json.dump(d, outfp)

    @staticmethod
    def save_gzip(clazz, inst, **kwargs):
        JsonSerializer.save(clazz, inst, gzip=True, **kwargs)

    @staticmethod
    def load(clazz, from_ext=None, from_mem=None, offset_mapper=None, gzip=False, **kwargs):
        print("RUNNING load with from_ext=", from_ext, " from_mem=", from_mem)

        if from_ext is not None and from_mem is not None:
            raise Exception("Exactly one of from_ext and from_mem must be specified ")
        if from_ext is None and from_mem is None:
            raise Exception("Exactly one of from_ext and from_mem must be specified ")

        isurl, extstr = is_url(from_ext)
        if from_ext is not None:
            if isurl:
                print("DEBUG: we got a URL")
                if gzip:
                    from_mem = get_bytes_from_url(extstr)
                else:
                    from_mem = get_str_from_url(extstr, encoding="utf-8")
            else:
                print("DEBUG: not a URL !!!")
        if from_mem:
            if gzip:
                d = json.loads(decompress(from_mem).decode("UTF-8"))
            else:
                d = json.loads(from_mem)
            doc = clazz.from_dict(d, offset_mapper=offset_mapper, **kwargs)
        else:  # from_ext must have been not None and a path
            if gzip:
                with gopen(extstr, "rt") as infp:
                    d = json.load(infp)
            else:
                with open(extstr, "rt") as infp:
                    d = json.load(infp)
            doc = clazz.from_dict(d, offset_mapper=offset_mapper, **kwargs)
        return doc

    @staticmethod
    def load_gzip(clazz, **kwargs):
        return JsonSerializer.load(clazz, gzip=True, **kwargs)


class PlainTextSerializer:

    @staticmethod
    def save(clazz, inst, to_ext=None, to_mem=None, offset_type=None, offset_mapper=None, gzip=False, **kwargs):
        txt = inst.text
        if txt is None:
            txt = ""
        if to_mem:
            if gzip:
                compress(txt.encode("UTF-8"))
            else:
                return txt
        else:
            if gzip:
                with gopen(to_ext, "wt") as outfp:
                    outfp.write(txt)
            else:
                with open(to_ext, "wt") as outfp:
                    outfp.write(txt)

    @staticmethod
    def save_gzip(clazz, inst, **kwargs):
        PlainTextSerializer.save(clazz, inst, gzip=True, **kwargs)

    @staticmethod
    def load(clazz, from_ext=None, from_mem=None, offset_mapper=None, gzip=False, **kwargs):
        isurl, extstr = is_url(from_ext)
        if from_ext is not None:
            if isurl:
                if gzip:
                    from_mem = get_bytes_from_url(extstr)
                else:
                    from_mem = get_str_from_url(extstr, encoding="utf-8")
        if from_mem:
            if gzip:
                txt = decompress(from_mem).decode("UTF-8")
            else:
                txt = from_mem
            doc = Document(txt)
        else:
            if gzip:
                with gopen(extstr, "rt") as infp:
                    txt = infp.read()
            else:
                with open(extstr, "rt") as infp:
                    txt = infp.read()
            doc = Document(txt)
        return doc

    @staticmethod
    def load_gzip(clazz, **kwargs):
        return PlainTextSerializer.load(clazz, gzip=True, **kwargs)


class YamlSerializer:

    @staticmethod
    def save(clazz, inst, to_ext=None, to_mem=None, offset_type=None, offset_mapper=None, gzip=False, **kwargs):
        d = inst.to_dict(offset_type=offset_type, offset_mapper=offset_mapper, **kwargs)
        if to_mem:
            if gzip:
                compress(yaml.dump(d).encode("UTF-8"))
            else:
                return yaml.dump(d)
        else:
            if gzip:
                with gopen(to_ext, "wt") as outfp:
                    yaml.dump(d, outfp)
            else:
                with open(to_ext, "wt") as outfp:
                    yaml.dump(d, outfp)

    @staticmethod
    def save_gzip(clazz, inst, **kwargs):
        YamlSerializer.save(clazz, inst, gzip=True, **kwargs)

    @staticmethod
    def load(clazz, from_ext=None, from_mem=None, offset_mapper=None, gzip=False, **kwargs):
        isurl, extstr = is_url(from_ext)
        if from_ext is not None:
            if isurl:
                if gzip:
                    from_mem = get_bytes_from_url(extstr)
                else:
                    from_mem = get_str_from_url(extstr, encoding="utf-8")
        if from_mem:
            if gzip:
                d = yaml.load(decompress(from_mem).decode("UTF-8"), Loader=yaml.FullLoader)
            else:
                d = yaml.load(from_mem, Loader=yaml.FullLoader)
            doc = clazz.from_dict(d, offset_mapper=offset_mapper, **kwargs)
        else:
            if gzip:
                with gopen(extstr, "rt") as infp:
                    d = yaml.load(infp, Loader=yaml.FullLoader)
            else:
                with open(extstr, "rt") as infp:
                    d = yaml.load(infp, Loader=yaml.FullLoader)
            doc = clazz.from_dict(d, offset_mapper=offset_mapper, **kwargs)
        return doc

    @staticmethod
    def load_gzip(clazz, **kwargs):
        return YamlSerializer.load(clazz, gzip=True, **kwargs)


MSGPACK_VERSION_HDR = "sm2"


class MsgPackSerializer:

    @staticmethod
    def document2stream(doc: Document, stream):
        pack(MSGPACK_VERSION_HDR, stream)
        pack(doc.offset_type, stream)
        pack(doc.text, stream)
        pack(doc.name, stream)
        pack(doc._features, stream)
        pack(len(doc._annotation_sets), stream)
        for name, annset in doc._annotation_sets:
            pack(name, stream)
            pack(annset.next_annid, stream)
            pack(len(annset), stream)
            for ann in annset.fast_iter():
                pack(ann.type, stream)
                pack(ann.start, stream)
                pack(ann.end, stream)
                pack(ann.id, stream)
                pack(ann.features, stream)

    @staticmethod
    def stream2document(stream):
        u = Unpacker(stream)
        version = u.unpack()
        if version != MSGPACK_VERSION_HDR:
            raise Exception("MsgPack data starts with wrong version")
        doc = Document()
        doc.offset_type = u.unpack()
        doc._text = u.unpack()
        doc.name = u.unpack()
        doc._features = u.unpack()
        nsets = u.unpack()
        setsdict = dict()
        doc.annotation_sets = setsdict
        for iset in range(nsets):
            sname = u.unpack()
            if sname is None:
                sname = ""
            annset = AnnotationSet(name=sname, owner_doc=doc)
            annset._next_annid = u.unpack()
            nanns = u.unpack()
            for iann in range(nanns):
                atype = u.unpack()
                astart = u.unpack()
                aend = u.unpack()
                aid = u.unpack()
                afeatures = u.unpack()
                ann = Annotation(astart, aend, atype, annid=aid, features=afeatures)
                annset._annotations[aid] = ann
            setsdict[sname] = annset
        return doc

    @staticmethod
    def save(clazz, inst, to_ext=None, to_mem=None, offset_type=None, offset_mapper=None, **kwargs):
        if isinstance(inst, Document):
            writer = MsgPackSerializer.document2stream
        elif isinstance(inst, ChangeLog):
            raise Exception("Not implemented yet")
        else:
            raise Exception("Object not supported")
        if to_mem:
            f = io.BytesIO()
        else:
            f = open(to_ext, "wb")
        writer(inst, f)
        if to_mem:
            return f.getvalue()
        else:
            f.close()

    @staticmethod
    def load(clazz, from_ext=None, from_mem=None, offset_mapper=None, **kwargs):
        if clazz == Document:
            reader = MsgPackSerializer.stream2document
        elif clazz == ChangeLog:
            raise Exception("Not implemented yet")
        else:
            raise Exception("Object not supported")

        isurl, extstr = is_url(from_ext)
        if from_ext is not None:
            if isurl:
                from_mem = get_bytes_from_url(extstr)
        if from_mem:
            f = io.BytesIO(from_mem)
        else:
            f = open(extstr, "rb")
        doc = reader(f)
        return doc

JS_JQUERY = '<script src="https://ajax.googleapis.com/ajax/libs/jquery/3.5.1/jquery.min.js"></script>'
JS_GATENLP = '<script src="https://unpkg.com/gatenlp-ann-viewer@1.0.8/gatenlp-ann-viewer.js"></script>'
HTML_TEMPLATE_FILE_NAME = "gatenlp-ann-viewer.html"
JS_GATENLP_FILE_NAME = "gatenlp-ann-viewer-merged.js"

html_ann_viewer_serializer_js_loaded = False


class HtmlAnnViewerSerializer:

    @staticmethod
    def save(clazz, inst, to_ext=None, to_mem=None, notebook=False, offline=False,
             htmlid=None, **kwargs):
        """
        Convert a document to HTML for visualizing it.

        :param clazz:
        :param inst:
        :param to_ext:
        :param to_mem:
        :param notebook:
        :param offline:
        :param htmlid: the id to use for HTML ids so it is possible to style the output
           from a separate notebook cell.
        :param kwargs:
        :return:
        """
        if not isinstance(inst, Document):
            raise Exception("Not a document!")
        doccopy = inst.deepcopy()
        doccopy.to_offset_type("j")
        json = doccopy.save_mem(fmt="json")
        htmlloc = os.path.join(os.path.dirname(__file__), "_htmlviewer", HTML_TEMPLATE_FILE_NAME)
        if not os.path.exists(htmlloc):
            raise Exception("Could not find HTML template, {} does not exist".format(htmlloc))
        with open(htmlloc, "rt", encoding="utf-8") as infp:
            html = infp.read();
        if notebook:
            str_start = "<!--STARTDIV-->"
            str_end = "<!--ENDDIV-->"
            idx1 = html.find(str_start) + len(str_start)
            idx2 = html.find(str_end)
            if htmlid:
                rndpref = str(htmlid)
            else:
                rndpref = "".join(choice(ascii_uppercase) for i in range(10))
            html = html[idx1:idx2]
            html = f"""<div><style>#{rndpref}-wrapper {{ color: yellow !important; }}</style>
<div id="{rndpref}-wrapper">
{html}
</div></div>"""
            # replace the prefix with a random one
            html = html.replace("GATENLPID", rndpref)
        if offline:
            global html_ann_viewer_serializer_js_loaded
            if not html_ann_viewer_serializer_js_loaded:
                jsloc = os.path.join(os.path.dirname(__file__), "_htmlviewer", JS_GATENLP_FILE_NAME)
                if not os.path.exists(jsloc):
                    raise Exception("Could not find JavsScript file, {} does not exist".format(jsloc))
                with open(jsloc, "rt", encoding="utf-8") as infp:
                    js = infp.read();
                    js = """<script type="text/javascript">""" + js + "</script>"
                html_ann_viewer_serializer_js_loaded = True
            else:
                js = ""
        else:
            js = JS_JQUERY + JS_GATENLP
        html = html.replace("$$JAVASCRIPT$$", js, 1).replace("$$JSONDATA$$", json, 1)
        if to_mem:
            return html
        else:
            with open(to_ext, "wt", encoding="utf-8") as outfp:
                outfp.write(html)


class HtmlLoader:

    @staticmethod
    def load_rendered(clazz, from_ext=None, from_mem=None, parser=None, markup_set_name="Original markups",
             process_soup=None, offset_mapper=None, **kwargs):
        raise Exception("Rendered html parser not yet implemented")

    @staticmethod
    def load(clazz, from_ext=None, from_mem=None, parser=None, markup_set_name="Original markups",
             process_soup=None, offset_mapper=None, **kwargs):
        """
        Load a HTML file.

        :param clazz:
        :param from_ext:
        :param from_mem:
        :param parser: one of "html.parser", "lxml", "lxml-xml", "html5lib" (default is "lxml")
        :param markup_set_name: the annotation set name for the set to contain the HTML annotations
        :param process_soup: a function to run on the parsed HTML soup before converting
        :param offset_mapper:
        :param kwargs:
        :return:
        """
        # NOTE: for now we have a simple heuristic for adding newlines to the text:
        # before and after a block element, a newline is added unless there is already one
        # NOTE: for now we use  multi_valued_attributes=None which prevents attributes of the
        # form "class='val1 val2'" to get converted into features with a list of values.
        isurl, extstr = is_url(from_ext)
        if from_ext is not None:
            if isurl:
                from_mem = get_str_from_url(extstr)
        if from_mem:
            bs = BeautifulSoup(from_mem, parser,  multi_valued_attributes=None)
        else:
            bs = BeautifulSoup(extstr, parser,  multi_valued_attributes=None)
        # we recursively iterate the tree depth first, going through the children
        # and adding to a list that either contains the text or a dict with the information
        # about annotations we want to add
        nlels = {
            "pre", "br", "p", "div", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "li",
            "address", "article", "aside", "blockquote", "del", "figure", "figcaption",
            "footer", "header", "hr", "ins", "main", "nav", "section", "summary", "input", "legend",
            "option", "textarea", "bdi", "bdo", "center", "code", "dfn", "menu", "dir", "caption",
        }
        ignoreels = {
            "script", "style"
        }
        docinfo = {"anninfos": [], "curoffset": 0, "curid": 0, "text": ""}
        def walktree(el):
            print("DEBUG: type=", type(el))
            if isinstance(el, bs4.element.Doctype):
                print("DEBUG: got doctype", type(el))
            elif isinstance(el, bs4.element.Comment):
                print("DEBUG: got Comment", type(el))
            elif isinstance(el, bs4.element.Script):
                print("DEBUG: got Script", type(el))
            elif isinstance(el, bs4.element.Tag):
                print("DEBUG: got tag: ", type(el), " name=",el.name)
                # some tags we ignore completely:
                if el.name in ignoreels:
                    return
                # for some tags we insert a new line before, but only if we do not already have one
                if not docinfo["text"].endswith("\n") and \
                        el.name in nlels:
                    docinfo["text"] += "\n"
                    print("DEBUG: adding newline before at ", docinfo["curoffset"])
                    docinfo["curoffset"] += 1
                ann = {"type": el.name, "features": el.attrs,
                       "id": docinfo["curid"], "event": "start", "start": docinfo["curoffset"]}
                thisid = docinfo["curid"]
                docinfo["anninfos"].append(ann)
                docinfo["curid"] += 1
                for child in el.children:
                    walktree(child)
                # for some tags we insert a new line after
                if not docinfo["text"].endswith("\n") and \
                        el.name in nlels:
                    docinfo["text"] += "\n"
                    print("DEBUG: adding newline after at ", docinfo["curoffset"])
                    docinfo["curoffset"] += 1
                docinfo["anninfos"].append({"event": "end", "id": thisid, "end": docinfo["curoffset"]})
            elif isinstance(el, bs4.element.NavigableString):
                # print("DEBUG: got text: ", el)
                text = str(el)
                if text == "\n" and docinfo["text"].endswith("\n"):
                    return
                docinfo["text"] += text
                docinfo["curoffset"] += len(el)
            else:
                print("WARNING: odd element type", type(el))
        walktree(bs)
        # need to add the end corresponding to bs
        # print("DEBUG: got docinfo:\n",docinfo)
        id2anninfo = {}  # from id to anninfo
        nstart = 0
        for anninfo in docinfo["anninfos"]:
            if anninfo["event"] == "start":
                nstart += 1
                id2anninfo[anninfo["id"]] = anninfo
        nend = 0
        for anninfo in docinfo["anninfos"]:
            if anninfo["event"] == "end":
                nend += 1
                end = anninfo["end"]
                annid = anninfo["id"]
                anninfo = id2anninfo[annid]
                anninfo["end"] = end
        # print("DEBUG: got nstart/nend", nstart, nend)
        assert nstart == nend
        # print("DEBUG: got id2anninfo:\n", id2anninfo)
        doc = Document(docinfo["text"])
        annset = doc.annset(markup_set_name)
        for i in range(nstart):
            anninfo = id2anninfo[i]
            annset.add(start=anninfo["start"], end=anninfo["end"], anntype=anninfo["type"],
                       features=anninfo["features"])
        return doc


class GateXmlLoader:

    @staticmethod
    def value4objectwrapper(text):
        """
        This may one day convert things like lists, maps, shared objects to Python, but for
        now we always throw an exeption.
        :param text:
        :return:
        """
        raise Exception("Cannot load GATE XML which contains gate.corpora.ObjectWrapper data")

    @staticmethod
    def load(clazz, from_ext=None, ignore_unknown_types=False):
        # TODO: the code below is just an outline and needs work!
        # TODO: make use of the test document created in repo project-python-gatenlp
        import xml.etree.ElementTree as ET
        isurl, extstr = is_url(from_ext)
        if isurl:
            xmlstring = get_str_from_url(extstr, encoding="utf-8")
            root = ET.fromstring(xmlstring)
        else:
            tree = ET.parse(extstr)
            root = tree.getroot()

        # or: root = ET.fromstring(xmlstring)

        # check we do have a GATE document

        assert root.tag == "GateDocument"
        assert root.attrib == {"version": "3"}

        def parsefeatures(feats):
            features = {}
            for feat in list(feats):
                name = None
                value = None
                for el in list(feat):
                    if el.tag == "Name":
                        if el.get("className") == "java.lang.String":
                            name = el.text
                        else:
                            raise Exception("Odd Feature Name type: " + el.get("className"))
                    elif el.tag == "Value":
                        cls_name = el.get("className")
                        if cls_name == "java.lang.String":
                            value = el.text
                        elif cls_name == "java.lang.Integer":
                            value = int(el.text)
                        elif cls_name == "java.lang.Long":
                            value = int(el.text)
                        elif cls_name == "java.math.BigDecimal":
                            value = float(el.text)
                        elif cls_name == "java.lang.Boolean":
                            value = bool(el.text)
                        #elif cls_name == "gate.corpora.ObjectWrapper":
                        #    value = GateXmlLoader.value4objectwrapper(el.text)
                        else:
                            if ignore_unknown_types:
                                print(f"Warning: ignoring feature with serialization type: {cls_name}", file=sys.stderr)
                            else:
                                raise Exception("Unsupported serialization type: " + el.get("className"))
                if name is not None and value is not None:
                    features[name] = value
            return features

        # get the document features
        docfeatures = {}
        feats = root.findall("./GateDocumentFeatures/Feature")

        docfeatures = parsefeatures(feats)

        textwithnodes = root.findall("./TextWithNodes")
        text = ""
        node2offset = {}
        curoff = 0
        for item in textwithnodes:
            if item.text:
                print("Got item text: ", item.text)
                text += item.text
                # TODO HTML unescape item text
                curoff += len(item.text)
            for node in item:
                nodeid = node.get("id")
                node2offset[nodeid] = curoff
                if node.tail:
                    # TODO: unescape item.text?
                    print("Gote node tail: ", node.tail)
                    text += node.tail
                    curoff += len(node.tail)

        annsets = root.findall("./AnnotationSet")

        annotation_sets = {}  # map name - set
        for annset in annsets:
            if annset.get("Name"):
                setname = annset.get("Name")
            else:
                setname = ""
            annots = annset.findall("./Annotation")
            annotations = []
            maxannid = 0
            for ann in annots:
                annid = int(ann.attrib["Id"])
                maxannid = max(maxannid, annid)
                anntype = ann.attrib["Type"]
                startnode = ann.attrib["StartNode"]
                endnode = ann.attrib["EndNode"]
                startoff = node2offset[startnode]
                endoff = node2offset[endnode]
                feats = ann.findall("./Feature")
                features = parsefeatures(feats)
                if len(features) == 0:
                    features = None
                annotation = {"id": annid, "type": anntype, "start": startoff, "end": endoff,
                              "features": features}
                annotations.append(annotation)
            annset = {"name": setname, "annotations": annotations, "next_annid": maxannid + 1}
            annotation_sets[setname] = annset

        docmap = {"text": text, "features": docfeatures, "offset_type": "p",
                  "annotation_sets": annotation_sets}

        doc = Document.from_dict(docmap)
        return doc


def determine_loader(clazz, from_ext=None, from_mem=None, offset_mapper=None, gzip=False, **kwargs):
    first = None
    if from_mem:
        first = from_mem[0]
    else:
        with open(from_ext, "rt") as infp:
            first = infp.read(1)
    if first == "{":
        return JsonSerializer.load(clazz, from_ext=from_ext, from_mem=from_mem, offset_mapper=offset_mapper,
                            gzip=gzip, **kwargs)
    else:
        return MsgPackSerializer.load(clazz, from_ext=from_ext, from_mem=from_mem, offset_mapper=offset_mapper,
                            gzip=gzip, **kwargs)


DOCUMENT_SAVERS = {
    "text/plain": PlainTextSerializer.save,
    "text/plain+gzip": PlainTextSerializer.save_gzip,
    "text": PlainTextSerializer.save,
    "bdocjs": JsonSerializer.save,
    "json": JsonSerializer.save,
    "jsongz": JsonSerializer.save_gzip,
    "yaml": YamlSerializer.save,
    "text/bdocym": YamlSerializer.save,
    "text/bdocym+gzip+": YamlSerializer.save,
    "text/bdocjs": JsonSerializer.save,
    "text/bdocjs+gzip": JsonSerializer.save_gzip,
    "msgpack": MsgPackSerializer.save,
    "application/msgpack": MsgPackSerializer.save,
    "html-ann-viewer": HtmlAnnViewerSerializer.save,
}
DOCUMENT_LOADERS = {
    "json": JsonSerializer.load,
    "bdocjs": JsonSerializer.load,
    "yaml": YamlSerializer.load,
    "text/bdocym": YamlSerializer.load,
    "text/bdocym+gzip": YamlSerializer.load_gzip,
    "jsongz": JsonSerializer.load_gzip,
    "yamlgz": YamlSerializer.load_gzip,
    "jsonormsgpack": determine_loader,
    "text/bdocjs": JsonSerializer.load,
    "text/plain": PlainTextSerializer.load,
    "text/plain+gzip": PlainTextSerializer.load_gzip,
    "text": PlainTextSerializer.load,
    "text/bdocjs+gzip": JsonSerializer.load_gzip,
    "msgpack": MsgPackSerializer.load,
    "application/msgpack": MsgPackSerializer.load,
    "text/html": HtmlLoader.load,
    "html": HtmlLoader.load,
    "html-rendered": HtmlLoader.load_rendered,
    "gatexml": GateXmlLoader.load,
}
CHANGELOG_SAVERS = {
    "json": JsonSerializer.save,
    "text/bdocjs+gzip": JsonSerializer.save_gzip,
    "text/bdocjs": JsonSerializer.save,
}
CHANGELOG_LOADERS = {
    "json": JsonSerializer.load,
    "text/bdocjs+gzip": JsonSerializer.load_gzip,
    "text/bdocjs": JsonSerializer.load,
}

# map extensions to document types
EXTENSIONS = {
    "bdocjs": "json",
    "bdocym": "yaml",
    "bdocym.gz": "text/bdocym+gzip",
    "bdoc.gz": "text/bdocjs+gzip", # lets assume it is compressed json
    "bdoc": "jsonormsgpack",
    "bdocjs.gz": "text/bdocjs+gzip",
    "bdocjson": "json",
    "bdocmp": "msgpack",
    "txt": "text/plain",
    "txt.gz": "text/plain+gzip",
    "html": "text/html",
    "htm": "text/html",
}


def get_handler(filespec, fmt, handlers, saveload, what):
    msg = f"Could not determine how to {saveload} {what} for format {fmt} in module gatenlp.serialization.default"
    if fmt:
        handler = handlers.get(fmt)
        if not handler:
            raise Exception(msg)
        return handler
    else:
        if not filespec: # in case of save_mem
            raise Exception(msg)
        if isinstance(filespec, os.PathLike):
            wf = os.fspath(filespec)
        elif isinstance(filespec, str):
            wf = filespec
        else:
            raise Exception(msg)
        name, ext = os.path.splitext(wf)
        if ext == ".gz":
            ext2 = os.path.splitext(name)[1]
            if ext2:
                ext2 = ext2[1:]
            ext = ext2 + ext
        elif ext:
            ext = ext[1:]
        fmt = EXTENSIONS.get(ext)
        msg = f"Could not determine how to {saveload} {what} for format {fmt} and with extension {ext} in module gatenlp.serialization.default"
        if not fmt:
            raise Exception(msg)
        handler = handlers.get(fmt)
        if not handler:
            raise Exception(msg)
        return handler


def get_document_saver(filespec, fmt):
    return get_handler(filespec, fmt, DOCUMENT_SAVERS, "save", "document")


def get_document_loader(filespec, fmt):
    return get_handler(filespec, fmt, DOCUMENT_LOADERS, "load", "document")


def get_changelog_saver(filespec, fmt):
    return get_handler(filespec, fmt, CHANGELOG_SAVERS, "save", "changelog")


def get_changelog_loader(filespec, fmt):
    return get_handler(filespec, fmt, CHANGELOG_LOADERS, "load", "changelog")