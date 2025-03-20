# -*- coding: utf-8 -*-
from __future__ import annotations

import math as Math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import (
        Any,
        Callable,
        Dict,
        Generator,
        List,
        Optional as Opt,
        Sequence as Seq,
        Tuple,
        TypeVar,
        Union,
    )

    T = TypeVar("T")
    Node = Union[str, DiagramItem]  # pylint: disable=used-before-assignment
    WriterF = Callable[[str], Any]
    WalkerF = Callable[[DiagramItem], Any]  # pylint: disable=used-before-assignment
    AttrsT = Dict[str, Any]

# Display constants
DEBUG = False  # if true, writes some debug information into attributes
VS = 8  # minimum vertical separation between things. For a 3px stroke, must be at least 4
AR = 10  # radius of arcs
DIAGRAM_CLASS = "railroad-diagram"  # class to put on the root <svg>
STROKE_ODD_PIXEL_LENGTH = (
    True  # is the stroke width an odd (1px, 3px, etc) pixel length?
)
INTERNAL_ALIGNMENT = (
    "center"  # how to align items when they have extra space. left/right/center
)
CHAR_WIDTH = 8.5  # width of each monospace character. play until you find the right value for your font
COMMENT_CHAR_WIDTH = 7  # comments are in smaller text by default
TERMINAL_ID_COUNTER = 1


def escapeAttr(val: Union[str, float]) -> str:
    if isinstance(val, str):
        return val.replace("&", "&amp;").replace("'", "&apos;").replace('"', "&quot;")
    return f"{val:g}"


def escapeHtml(val: str) -> str:
    return escapeAttr(val).replace("<", "&lt;")


def determineGaps(outer: float, inner: float) -> Tuple[float, float]:
    diff = outer - inner
    if INTERNAL_ALIGNMENT == "left":
        return 0, diff
    elif INTERNAL_ALIGNMENT == "right":
        return diff, 0
    else:
        return diff / 2, diff / 2


def doubleenumerate(seq: Seq[T]) -> Generator[Tuple[int, int, T], None, None]:
    length = len(list(seq))
    for i, item in enumerate(seq):
        yield i, i - length, item


def addDebug(el: DiagramItem) -> None:
    if not DEBUG:
        return
    el.attrs["data-x"] = "{0} w:{1} h:{2}/{3}/{4}".format(
        type(el).__name__, el.width, el.up, el.height, el.down
    )


class DiagramItem:
    def __init__(self, name: str, attrs: Opt[AttrsT] = None, text: Opt[Node] = None):
        self.name = name
        # up = distance it projects above the entry line
        self.up: float = 0
        # height = distance between the entry/exit lines
        self.height: float = 0
        # down = distance it projects below the exit line
        self.down: float = 0
        # width = distance between the entry/exit lines horizontally
        self.width: float = 0
        # Whether the item is okay with being snug against another item or not
        self.needsSpace = False

        # DiagramItems pull double duty as SVG elements.
        self.attrs: AttrsT = attrs or {}
        # Subclasses store their meaningful children as .item or .items;
        # .children instead stores their formatted SVG nodes.
        self.children: List[Union[Node, Path, Style]] = [text] if text else []

    def format(self, x: float, y: float, width: float) -> DiagramItem:
        raise NotImplementedError  # Virtual

    def addTo(self, parent: DiagramItem) -> DiagramItem:
        parent.children.append(self)
        return self

    def writeSvg(self, write: WriterF) -> None:
        # Открытие тега с атрибутами в одной строке для компактности
        attrs = " ".join(f'{name}="{escapeAttr(value)}"' for name, value in sorted(self.attrs.items()))
        write(f"<{self.name} {attrs}>")

        for child in self.children:
            if isinstance(child, (DiagramItem, Path, Style)):
                write("\n  ")  # Отступ для вложенных элементов
                child.writeSvg(write)
            else:
                write(escapeHtml(child))

        write(f"</{self.name}>")

    def walk(self, cb: WalkerF) -> None:
        cb(self)


class DiagramMultiContainer(DiagramItem):
    def __init__(
            self,
            name: str,
            items: Seq[Node],
            attrs: Opt[Dict[str, str]] = None,
            text: Opt[str] = None,
    ):
        DiagramItem.__init__(self, name, attrs, text)
        self.items: List[DiagramItem] = [wrapString(item) for item in items]

    def format(self, x: float, y: float, width: float) -> DiagramItem:
        raise NotImplementedError  # Virtual

    def walk(self, cb: WalkerF) -> None:
        cb(self)
        for item in self.items:
            item.walk(cb)


class Path:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.attrs = {"d": f"M{x} {y}"}

    def m(self, x: float, y: float) -> Path:
        self.attrs["d"] += f"m{x} {y}"
        return self

    def l(self, x: float, y: float) -> Path:
        self.attrs["d"] += f"l{x} {y}"
        return self

    def h(self, val: float, start_marker: bool = False, end_marker: bool = False, reverse: bool = False,
          far: bool = False) -> Path:
        """Горизонтальная линия с маркером на конце."""
        self.attrs["d"] += f"h{val}"
        if start_marker:
            self.add_start_marker(reverse=reverse, far=far)
        if end_marker:
            self.add_end_marker(reverse=reverse, far=far)
        return self

    def v(self, val: float, start_marker: bool = False, end_marker: bool = False, reverse: bool = False,
          far: bool = False) -> Path:
        """Вертикальная линия с маркером на конце."""
        self.attrs["d"] += f"v{val}"
        if start_marker:
            self.add_start_marker(reverse=reverse, far=far)
        if end_marker:
            self.add_end_marker(reverse=reverse, far=far)
        return self

    def right(self, val: float, start_marker: bool = False, end_marker: bool = False, reverse: bool = False,
              far: bool = False) -> Path:
        """Создает правую горизонтальную линию с маркером."""
        return self.h(max(0, val), start_marker=start_marker, end_marker=end_marker, reverse=reverse, far=far)

    def left(self, val: float, start_marker: bool = False, end_marker: bool = False, reverse: bool = False,
             far: bool = False) -> Path:
        """Создает левую горизонтальную линию с маркером."""
        return self.h(-max(0, val), start_marker=start_marker, end_marker=end_marker, reverse=reverse, far=far)

    def down(self, val: float, start_marker: bool = False, end_marker: bool = False, reverse: bool = False,
             far: bool = False) -> Path:
        """Создает вертикальную линию вниз с маркером."""
        return self.v(max(0, val), start_marker=start_marker, end_marker=end_marker, reverse=reverse, far=far)

    def up(self, val: float, start_marker: bool = False, end_marker: bool = False, reverse: bool = False,
           far: bool = False) -> Path:
        """Создает вертикальную линию вверх с маркером."""
        return self.v(-max(0, val), start_marker=start_marker, end_marker=end_marker, reverse=reverse, far=far)

    def add_start_marker(self, reverse: bool = False, far: bool = False) -> Path:
        """Добавить маркер на начало пути."""
        if far:
            self.attrs["marker-start"] = "url(#far-arrow)"
        elif reverse:
            self.attrs["marker-start"] = "url(#reverse-arrow)"
        else:
            self.attrs["marker-start"] = "url(#arrow)"
        return self

    def add_end_marker(self, reverse: bool = False, far: bool = False) -> Path:
        """Добавить маркер на конец пути."""
        if far:
            self.attrs["marker-end"] = "url(#far-arrow)"
        elif reverse:
            self.attrs["marker-end"] = "url(#reverse-arrow)"
        else:
            self.attrs["marker-end"] = "url(#arrow)"
        return self

    def arc_8(self, start: str, dir: str) -> Path:
        # 1/8 of a circle
        arc = AR
        s2 = 1 / Math.sqrt(2) * arc
        s2inv = arc - s2
        sweep = "1" if dir == "cw" else "0"
        path = f"a {arc} {arc} 0 0 {sweep} "
        sd = start + dir
        offset: List[float]
        if sd == "ncw":
            offset = [s2, s2inv]
        elif sd == "necw":
            offset = [s2inv, s2]
        elif sd == "ecw":
            offset = [-s2inv, s2]
        elif sd == "secw":
            offset = [-s2, s2inv]
        elif sd == "scw":
            offset = [-s2, -s2inv]
        elif sd == "swcw":
            offset = [-s2inv, -s2]
        elif sd == "wcw":
            offset = [s2inv, -s2]
        elif sd == "nwcw":
            offset = [s2, -s2inv]
        elif sd == "nccw":
            offset = [-s2, s2inv]
        elif sd == "nwccw":
            offset = [-s2inv, s2]
        elif sd == "wccw":
            offset = [s2inv, s2]
        elif sd == "swccw":
            offset = [s2, s2inv]
        elif sd == "sccw":
            offset = [s2, -s2inv]
        elif sd == "seccw":
            offset = [s2inv, -s2]
        elif sd == "eccw":
            offset = [-s2inv, -s2]
        elif sd == "neccw":
            offset = [-s2, -s2inv]

        path += " ".join(str(x) for x in offset)
        self.attrs["d"] += path
        return self

    def arc(self, sweep: str, start_marker: bool = False, end_marker: bool = False, reverse: bool = False) -> Path:
        """Дуга с маркером на начале или конце."""
        x = AR
        y = AR
        if sweep[0] == "e" or sweep[1] == "w":
            x *= -1
        if sweep[0] == "s" or sweep[1] == "n":
            y *= -1
        cw = 1 if sweep in ("ne", "es", "sw", "wn") else 0
        self.attrs["d"] += f"a{AR} {AR} 0 0 {cw} {x} {y}"

        if start_marker:
            self.add_start_marker(reverse=reverse)
        if end_marker:
            self.add_end_marker(reverse=reverse)

        return self

    def addTo(self, parent: DiagramItem) -> Path:
        parent.children.append(self)
        return self

    def writeSvg(self, write: WriterF) -> None:
        write("<path")
        for name, value in sorted(self.attrs.items()):
            write(f' {name}="{escapeAttr(value)}"')
        write(" />")

    def format(self) -> Path:
        self.attrs["d"] += "h.5"
        return self

    def __repr__(self) -> str:
        return f"Path({repr(self.x)}, {repr(self.y)})"


def wrapString(value: Node) -> DiagramItem:
    return value if isinstance(value, DiagramItem) else Terminal(value)


DEFAULT_STYLE = """\
	svg.railroad-diagram {
		background-color:hsl(30,20%,95%);
	}
	svg.railroad-diagram path {
		stroke-width:3;
		stroke:black;
		fill:rgba(0,0,0,0);
	}
	svg.railroad-diagram text {
		font:bold 14px monospace;
		text-anchor:middle;
	}
	svg.railroad-diagram text.label{
		text-anchor:start;
	}
	svg.railroad-diagram text.comment{
		font:italic 12px monospace;
	}
	svg.railroad-diagram rect{
		stroke-width:3;
		stroke:black;
		fill:hsl(120,100%,90%);
	}
	svg.railroad-diagram rect.group-box {
		stroke: gray;
		stroke-dasharray: 10 5;
		fill: none;
	}
    marker#arrow path {
        d: path("M 0 0 L 10 5 L 0 10 Z");
    }
    marker#reverse-arrow path {
        d: path("M 0 0 L 10 5 L 0 10 Z");
    }
    marker#far-arrow path {
        d: path("M 0 0 L 10 5 L 0 10 Z");
    }
"""


class Style:
    def __init__(self, css: str):
        self.css = css

    def __repr__(self) -> str:
        return f"Style({repr(self.css)})"

    def addTo(self, parent: DiagramItem) -> Style:
        parent.children.append(self)
        return self

    def format(self) -> Style:
        return self

    def writeSvg(self, write: WriterF) -> None:
        # Write included stylesheet as CDATA. See https:#developer.mozilla.org/en-US/docs/Web/SVG/Element/style
        cdata = "/* <![CDATA[ */\n{css}\n/* ]]> */\n".format(css=self.css)
        write("<style>{cdata}</style>".format(cdata=cdata))


class Diagram(DiagramMultiContainer):
    def __init__(self, *items: Node, **kwargs: str):
        # Accepts a type=[simple|complex] kwarg
        DiagramMultiContainer.__init__(
            self,
            "svg",
            list(items),
            {
                "class": DIAGRAM_CLASS,
            },
        )
        self.type = kwargs.get("type", "simple")
        if items and not isinstance(items[0], Start):
            self.items.insert(0, Start(self.type))
        if items and not isinstance(items[-1], End):
            self.items.append(End(self.type))
        self.up = 0
        self.down = 0
        self.height = 0
        self.width = 0
        for item in self.items:
            if isinstance(item, Style):
                continue
            self.width += item.width + (20 if item.needsSpace else 0)
            self.up = max(self.up, item.up - self.height)
            self.height += item.height
            self.down = max(self.down - item.height, item.down)
        if self.items[0].needsSpace:
            self.width -= 10
        if self.items[-1].needsSpace:
            self.width -= 10
        self.formatted = False

    def __repr__(self) -> str:
        items = ", ".join(map(repr, self.items[1:-1]))
        pieces = [] if not items else [items]
        if self.type != "simple":
            pieces.append(f"type={repr(self.type)}")
        return f'Diagram({", ".join(pieces)})'

    def format(
            self,
            paddingTop: float = 20,
            paddingRight: Opt[float] = None,
            paddingBottom: Opt[float] = None,
            paddingLeft: Opt[float] = None,
    ) -> Diagram:
        if paddingRight is None:
            paddingRight = paddingTop
        if paddingBottom is None:
            paddingBottom = paddingTop
        if paddingLeft is None:
            paddingLeft = paddingRight
        assert paddingRight is not None
        assert paddingBottom is not None
        assert paddingLeft is not None
        x = paddingLeft
        y = paddingTop + self.up
        g = DiagramItem("g")
        if STROKE_ODD_PIXEL_LENGTH:
            g.attrs["transform"] = "translate(.5 .5)"
        for item in self.items:
            if item.needsSpace:
                Path(x, y).h(10).addTo(g)
                x += 10
            item.format(x, y, item.width).addTo(g)
            x += item.width
            y += item.height
            if item.needsSpace:
                Path(x, y).h(10).addTo(g)
                x += 10
        self.attrs["width"] = str(self.width + paddingLeft + paddingRight)
        self.attrs["height"] = str(
            self.up + self.height + self.down + paddingTop + paddingBottom
        )
        self.attrs["viewBox"] = f"0 0 {self.attrs['width']} {self.attrs['height']}"
        g.addTo(self)
        self.formatted = True
        return self

    def writeSvg(self, write: WriterF) -> None:
        if not self.formatted:
            self.format()
        return DiagramItem.writeSvg(self, write)

    def writeStandalone(self, write: WriterF, css: str | None = None) -> None:
        if not self.formatted:
            self.format()
        if css is None:
            css = DEFAULT_STYLE
        Style(css).addTo(self)

        # Определение маркеров стрелок
        arrow_defs = DiagramItem("defs")

        # Треугольник в конце пути
        arrow_marker = DiagramItem("marker", {
            "id": "arrow",
            "viewBox": "0 0 10 10",
            "refX": "-5",  # Центр треугольника
            "refY": "5",
            "markerWidth": "3",
            "markerHeight": "3",
            "orient": "auto"
        })
        arrow_path = DiagramItem("polygon", {
            "points": "0,0 10,5 0,10",  # Указание координат треугольника
            "fill": "black"
        })
        arrow_path.addTo(arrow_marker)
        arrow_marker.addTo(arrow_defs)

        # Добавить аналогичный reverse-arrow и far-arrow
        reverse_arrow_marker = DiagramItem("marker", {
            "id": "reverse-arrow",
            "viewBox": "0 0 10 10",
            "refX": "-5",
            "refY": "5",
            "markerWidth": "3",
            "markerHeight": "3",
            "orient": "auto-start-reverse"
        })
        reverse_arrow_path = DiagramItem("polygon", {
            "points": "0,0 10,5 0,10",
            "fill": "black"
        })
        reverse_arrow_path.addTo(reverse_arrow_marker)
        reverse_arrow_marker.addTo(arrow_defs)

        far_arrow_marker = DiagramItem("marker", {
            "id": "far-arrow",
            "viewBox": "0 0 10 10",
            "refX": "-5",  # Дальняя привязка для треугольника
            "refY": "5",
            "markerWidth": "3",
            "markerHeight": "3",
            "orient": "auto"
        })
        far_arrow_path = DiagramItem("polygon", {
            "points": "0,0 10,5 0,10",
            "fill": "black"
        })
        far_arrow_path.addTo(far_arrow_marker)
        far_arrow_marker.addTo(arrow_defs)

        arrow_defs.addTo(self)

        # Установить более тонкие пути
        self.attrs["xmlns"] = "http://www.w3.org/2000/svg"
        self.attrs['xmlns:xlink'] = "http://www.w3.org/1999/xlink"
        DiagramItem.writeSvg(self, write)
        self.children.pop()
        del self.attrs["xmlns"]
        del self.attrs["xmlns:xlink"]


class Sequence(DiagramMultiContainer):
    def __init__(self, *items: Node):
        DiagramMultiContainer.__init__(self, "g", items)
        self.needsSpace = True
        self.up = 0
        self.down = 0
        self.height = 0
        self.width = 0
        for item in self.items:
            self.width += item.width + (20 if item.needsSpace else 0)
            self.up = max(self.up, item.up - self.height)
            self.height += item.height
            self.down = max(self.down - item.height, item.down)
        if self.items[0].needsSpace:
            self.width -= 10
        if self.items[-1].needsSpace:
            self.width -= 10
        addDebug(self)

    def __repr__(self) -> str:
        items = ", ".join(repr(item) for item in self.items)
        return f"Sequence({items})"

    def format(self, x: float, y: float, width: float) -> Sequence:
        leftGap, rightGap = determineGaps(width, self.width)
        Path(x, y).h(leftGap).addTo(self)
        Path(x + leftGap + self.width, y + self.height).h(rightGap).addTo(self)
        x += leftGap

        for i, item in enumerate(self.items):
            if item.needsSpace and i > 0:
                Path(x, y).h(10).addTo(self)
                x += 10
            item.format(x, y, item.width).addTo(self)
            x += item.width
            y += item.height
            if item.needsSpace and i < len(self.items) - 1:
                Path(x, y).h(10).addTo(self)
                x += 10
        return self


class Choice(DiagramMultiContainer):
    def __init__(self, default: int, *items: Node):
        DiagramMultiContainer.__init__(self, "g", items)
        assert default < len(items)
        self.default = default
        self.width = AR * 4 + max(item.width for item in self.items)
        self.up = self.items[0].up
        self.down = self.items[-1].down
        self.height = self.items[default].height
        for i, item in enumerate(self.items):
            if i in [default - 1, default + 1]:
                arcs = AR * 2
            else:
                arcs = AR
            if i < default:
                self.up += max(
                    arcs, item.height + item.down + VS + self.items[i + 1].up
                )
            elif i == default:
                continue
            else:
                self.down += max(
                    arcs,
                    item.up + VS + self.items[i - 1].down + self.items[i - 1].height,
                )
        self.down -= self.items[default].height  # already counted in self.height
        addDebug(self)

    def __repr__(self) -> str:
        items = ", ".join(repr(item) for item in self.items)
        return "Choice(%r, %s)" % (self.default, items)

    def format(self, x: float, y: float, width: float) -> Choice:
        leftGap, rightGap = determineGaps(width, self.width)

        # Hook up the two sides if self is narrower than its stated width.
        Path(x, y).h(leftGap).addTo(self)
        Path(x + leftGap + self.width, y + self.height).h(rightGap).addTo(self)
        x += leftGap

        innerWidth = self.width - AR * 4
        default = self.items[self.default]

        # Do the elements that curve above
        above = self.items[: self.default][::-1]
        if above:
            distanceFromY = max(
                AR * 2, default.up + VS + above[0].down + above[0].height
            )
        for i, ni, item in doubleenumerate(above):
            Path(x, y).arc("se", end_marker=True).up(distanceFromY - AR * 2).arc("wn").addTo(self)
            item.format(x + AR * 2, y - distanceFromY, innerWidth).addTo(self)
            Path(x + AR * 2 + innerWidth, y - distanceFromY + item.height).arc(
                "ne"
            ).down(distanceFromY - item.height + default.height - AR * 2).arc(
                "ws"
            ).addTo(
                self
            )
            if ni < -1:
                distanceFromY += max(
                    AR, item.up + VS + above[i + 1].down + above[i + 1].height
                )

        # Do the straight-line path.
        Path(x, y).right(AR * 2).addTo(self)
        self.items[self.default].format(x + AR * 2, y, innerWidth).addTo(self)
        Path(x + AR * 2 + innerWidth, y + self.height).right(AR * 2).addTo(self)

        # Do the elements that curve below
        below = self.items[self.default + 1:]
        if below:
            distanceFromY = max(
                AR * 2, default.height + default.down + VS + below[0].up
            )
        for i, item in enumerate(below):
            Path(x, y).arc("ne").down(distanceFromY - AR * 2).arc("ws").addTo(self)
            item.format(x + AR * 2, y + distanceFromY, innerWidth).addTo(self)
            Path(x + AR * 2 + innerWidth, y + distanceFromY + item.height).arc("se").up(
                distanceFromY - AR * 2 + item.height - default.height
            ).arc("wn").addTo(self)
            distanceFromY += max(
                AR,
                item.height
                + item.down
                + VS
                + (below[i + 1].up if i + 1 < len(below) else 0),
            )
        return self


def Optional(item: Node, skip: bool = False) -> Choice:
    return Choice(0 if skip else 1, Skip(), item)


class OneOrMore(DiagramItem):
    def __init__(self, item: Node, repeat: Opt[Node] = None):
        DiagramItem.__init__(self, "g")
        self.item = wrapString(item)
        repeat = repeat or Skip()
        self.rep = wrapString(repeat)
        self.width = max(self.item.width, self.rep.width) + AR * 2
        self.height = self.item.height
        self.up = self.item.up
        self.down = max(
            AR * 2, self.item.down + VS + self.rep.up + self.rep.height + self.rep.down
        )
        self.needsSpace = True
        addDebug(self)

    def format(self, x: float, y: float, width: float) -> OneOrMore:
        leftGap, rightGap = determineGaps(width, self.width)

        Path(x, y).h(leftGap).addTo(self)
        Path(x + leftGap + self.width, y + self.height).h(rightGap).addTo(self)
        x += leftGap

        Path(x, y).right(AR).addTo(self)
        self.item.format(x + AR, y, self.width - AR * 2).addTo(self)
        Path(x + self.width - AR, y + self.height).right(AR).addTo(self)

        # Обратная стрелка на повторе
        distanceFromY = max(AR * 2, self.item.height + self.item.down + VS + self.rep.up)
        Path(x + AR, y).arc("nw").down(distanceFromY - AR * 2).arc("ws", ).addTo(self)
        self.rep.format(x + AR, y + distanceFromY, self.width - AR * 2).addTo(self)
        Path(x + self.width - AR, y + distanceFromY + self.rep.height).arc("se").up(
            distanceFromY - AR * 2 + self.rep.height - self.item.height, start_marker=True, reverse=True
        ).arc("en").addTo(self)

        return self

    def walk(self, cb: WalkerF) -> None:
        cb(self)
        self.item.walk(cb)
        self.rep.walk(cb)

    def __repr__(self) -> str:
        return f"OneOrMore({repr(self.item)}, repeat={repr(self.rep)})"


def ZeroOrMore(item: Node, repeat: Opt[Node] = None, skip: bool = False) -> Choice:
    result = Optional(OneOrMore(item, repeat), skip)
    return result


class Start(DiagramItem):
    def __init__(self, type: str = "simple", label: Opt[str] = None):
        DiagramItem.__init__(self, "g")
        if label:
            self.width = max(20, len(label) * CHAR_WIDTH + 10)
        else:
            self.width = 20
        self.up = 10
        self.down = 10
        self.type = type
        self.label = label
        addDebug(self)

    def format(self, x: float, y: float, width: float) -> Start:
        path = Path(x, y - 10)
        if self.type == "complex":
            path.down(20).m(0, -10).right(self.width).addTo(self)
        else:
            path.down(20).m(10, -20).down(20).m(-10, -10).right(self.width).addTo(self)
        if self.label:
            DiagramItem(
                "text",
                attrs={"x": x, "y": y - 15, "style": "text-anchor:start"},
                text=self.label,
            ).addTo(self)
        return self

    def __repr__(self) -> str:
        return f"Start(type={repr(self.type)}, label={repr(self.label)})"


class End(DiagramItem):
    def __init__(self, type: str = "simple"):
        DiagramItem.__init__(self, "path")
        self.width = 20
        self.up = 10
        self.down = 10
        self.type = type
        addDebug(self)

    def format(self, x: float, y: float, width: float) -> End:
        if self.type == "simple":
            self.attrs["d"] = "M {0} {1} h 20 m -10 -10 v 20 m 10 -20 v 20".format(x, y)
        elif self.type == "complex":
            self.attrs["d"] = "M {0} {1} h 20 m 0 -10 v 20".format(x, y)
        return self

    def __repr__(self) -> str:
        return f"End(type={repr(self.type)})"


class Terminal(DiagramItem):
    def __init__(
            self, text: str, href: Opt[str] = None, title: Opt[str] = None, cls: str = ""
    ):
        global TERMINAL_ID_COUNTER
        DiagramItem.__init__(self, "g", {"class": " ".join(["terminal", cls])})
        self.text = text
        self.href = href
        self.title = title
        self.cls = cls
        self.width = len(text) * CHAR_WIDTH + 20
        self.up = 11
        self.down = 11
        self.needsSpace = True
        self.id = TERMINAL_ID_COUNTER
        TERMINAL_ID_COUNTER += 1
        self.attrs["id"] = f"{self.id}"
        addDebug(self)

    def __repr__(self) -> str:
        return (
            f"Terminal({repr(self.text)}, href={repr(self.href)}, "
            f"title={repr(self.title)}, cls={repr(self.cls)}, id={self.id})"
        )

    def format(self, x: float, y: float, width: float) -> Terminal:
        leftGap, rightGap = determineGaps(width, self.width)

        # Hook up the two sides if self is narrower than its stated width.
        Path(x, y).h(leftGap).addTo(self)
        Path(x + leftGap + self.width, y).h(rightGap).addTo(self)

        DiagramItem(
            "rect",
            {
                "x": x + leftGap,
                "y": y - 11,
                "width": self.width,
                "height": self.up + self.down,
                "rx": 10,
                "ry": 10,
            },
        ).addTo(self)
        text = DiagramItem(
            "text", {"x": x + leftGap + self.width / 2, "y": y + 4}, self.text
        )
        if self.href is not None:
            a = DiagramItem("a", {"xlink:href": self.href}, text).addTo(self)
            text.addTo(a)
        else:
            text.addTo(self)
        if self.title is not None:
            DiagramItem("title", {}, self.title).addTo(self)
        return self


class Skip(DiagramItem):
    def __init__(self) -> None:
        DiagramItem.__init__(self, "g")
        self.width = 0
        self.up = 0
        self.down = 0
        addDebug(self)

    def format(self, x: float, y: float, width: float) -> Skip:
        Path(x, y).right(width).addTo(self)
        return self

    def __repr__(self) -> str:
        return "Skip()"


def get_terminal_ids(diagram: DiagramItem) -> list:
    """
    Обходит дерево диаграммы и возвращает список строк формата "текст - id"
    для каждого терминала.
    """
    terminals = []

    def visitor(item: DiagramItem):
        if isinstance(item, Terminal):
            terminals.append(item.id)

    diagram.walk(visitor)
    return terminals
