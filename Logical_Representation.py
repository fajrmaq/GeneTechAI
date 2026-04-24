import matplotlib
matplotlib.use('Agg')
import sys
from pathlib import Path

try:
    import SchemDraw as schem
    import SchemDraw.logic as l
    import SchemDraw.elements as e
except ModuleNotFoundError:
    project_root = Path(__file__).resolve().parent.parent
    legacy_paths = []
    lib_dir = project_root / ".venv" / "lib"
    if lib_dir.exists():
        legacy_paths.extend(sorted(lib_dir.glob("python*/site-packages")))
    for site_packages in legacy_paths:
        if site_packages.exists() and str(site_packages) not in sys.path:
            sys.path.insert(0, str(site_packages))
    import SchemDraw as schem
    import SchemDraw.logic as l
    import SchemDraw.elements as e

from functions import *


class Logical_Representation:
    def __init__(self, total_gates, total_time, option, num):
        DeleteExistingImages()
        circuits = ReadFile()
        self.plot(circuits, total_gates, total_time, option, num)

    def plot(self, circuits, total_gates, total_time, option, num):
        col_map = {}
        col_map[0] = '#e31414'
        col_map[1] = '#34e681'
        col_map[2] = '#34a4e6'
        col_map[3] = '#ff7b00'
        col_map[4] = '#44855a'
        col_map[5] = '#1831c4'
        col_map[6] = '#9918c4'
        col_map[7] = '#e6178f'
        col_map[8] = '#995f81'

        for i in range(len(circuits)):
            file_num = i + 1
            if Total_Gates(i) <= total_gates and Total_time(i) <= total_time and file_num <= num:
                d = schem.Drawing(unit=.25, fontsize=7)
                G1 = 0
                G4 = G1
                use = []
                color = 0
                nor_color = 0
                for j in range(len(circuits[i])):
                    if j == 0:
                        all_gates = circuits[i][0].split(' ----|')
                        fp = all_gates[-1].split('-> ')[-1]
                        for k in range(len(all_gates)):
                            gate = all_gates[k].split('-> ')
                            if len(circuits[i]) > 1 and k == len(all_gates) - 2:
                                endbracket2 = len(circuits[i][1]) - circuits[i][1][-1::-1].index(")")
                                all_gates2 = circuits[i][1][:endbracket2].split(' ----|')
                                if len(all_gates2) >= len(all_gates) - 1:
                                    if 'P' + all_gates2[-1].split('-> ')[-1][1:-1] == gate[1]:
                                        d.add(e.LINE, d='right', l=3)
                            if fp not in gate[-1]:
                                if len(gate) == 2:
                                    delay = Delay(gate[0], gate[1])
                                    if k == 0:
                                        G1 = d.add(e.LINE, d='right', toplabel=gate[0])
                                        xx = d.add(e.LINE, d='right', l=0.5)
                                    else:
                                        xx = d.add(e.LINE, d='right', l=0.5, toplabel=gate[0])
                                    not_gate = d.add(
                                        l.NOT,
                                        zoom=1,
                                        endpts=[xx.end, [xx.end[0] + 3, xx.end[1]]],
                                        botlabel=gate[1],
                                        fill=col_map[color],
                                        toplabel=delay,
                                    )
                                    color += 1
                                    d.add(e.LINE, d='right', xy=not_gate.out)

                                elif len(gate) == 3:
                                    delay = Delay(gate[0], gate[2], gate[1])
                                    if k == 0:
                                        G1 = d.add(e.LINE, d='right', toplabel=gate[0])
                                        d.add(e.LINE, d='right', l=1.5)
                                    else:
                                        d.add(e.LINE, d='right', l=1.5, toplabel=gate[0])
                                    if gate[1] in baseList():
                                        nor_gate = d.add(l.NOR2, anchor='in1', zoom=1, botlabel=gate[2], fill=col_map[color], toplabel=delay)
                                        g3 = d.add(e.LINE, xy=nor_gate.in2, d='left', toplabel=gate[1])
                                        down_line_key = d.add(e.LINE, xy=g3.end, d='down')
                                        use.append((gate[1], down_line_key, col_map[color]))
                                        color += 1
                                    else:
                                        nor_gate = d.add(l.NOR2, anchor='in1', zoom=1, botlabel=gate[2], fill=col_map[color + 1], toplabel=delay)
                                        g3 = d.add(e.LINE, xy=nor_gate.in2, d='left', toplabel=gate[1])
                                        down_line_key = d.add(e.LINE, xy=g3.end, d='down')
                                        use.append((gate[1], down_line_key, col_map[color]))
                                        color += 2
                                    d.add(e.LINE, xy=nor_gate.out, d='right')

                            else:
                                if len(gate) == 2:
                                    d.add(e.LINE, d='right', l=1.5, toplabel=gate[0])

                                elif len(gate) == 3:
                                    d.add(e.LINE, d='right', l=1.5, toplabel=gate[0])
                                    or_gate = d.add(l.OR2, anchor='in1', zoom=1)
                                    g3 = d.add(e.LINE, xy=or_gate.in2, d='left', toplabel=gate[1])
                                    down_line_key = d.add(e.LINE, xy=g3.end, d='down')
                                    use.append((gate[1], down_line_key, col_map[color]))
                                    color += 1
                                    d.add(e.LINE, xy=or_gate.out, d='right')

                    else:
                        endbracket = len(circuits[i][j]) - circuits[i][j][-1::-1].index(")")
                        all_gates = circuits[i][j][:endbracket].split(' ----|')
                        for k in range(len(all_gates)):
                            gate = all_gates[k].split('-> ')
                            if len(gate) == 2:
                                delay = Delay(gate[0], gate[1])
                                if k == 0:
                                    if j == len(circuits[i]) - 1:
                                        G4 = d.add(e.LINE, d='right', toplabel=gate[0], xy=[G1.start[0], G1.end[1] - 2])
                                    else:
                                        G4 = d.add(e.LINE, d='right', toplabel=gate[0], xy=[G1.start[0], G1.end[1] - 4])
                                        nor_color = -1
                                    xx = d.add(e.LINE, d='right', l=0.5, xy=G4.end)
                                    if k == len(all_gates) - 1:
                                        if use[nor_color][0] in baseList():
                                            nor_color += 1
                                        not_gate = d.add(
                                            l.NOT,
                                            zoom=1,
                                            endpts=[xx.end, [xx.end[0] + 3, xx.end[1]]],
                                            botlabel=gate[1],
                                            fill=use[nor_color][2],
                                            toplabel=delay,
                                        )
                                        nor_color -= 1
                                    else:
                                        not_gate = d.add(
                                            l.NOT,
                                            zoom=1,
                                            botlabel=gate[1],
                                            endpts=[xx.end, [xx.end[0] + 3, xx.end[1]]],
                                            fill=col_map[color],
                                            toplabel=delay,
                                        )
                                        color += 1
                                else:
                                    xx = d.add(e.LINE, d='right', l=0.5, toplabel=gate[0], xy=G5.end)
                                    if k == len(all_gates) - 1:
                                        nor_color = 0
                                        not_gate = d.add(
                                            l.NOT,
                                            zoom=1,
                                            endpts=[xx.end, [xx.end[0] + 3, xx.end[1]]],
                                            botlabel=gate[1],
                                            fill=use[nor_color][2],
                                            toplabel=delay,
                                        )
                                        nor_color -= 1
                                    else:
                                        not_gate = d.add(
                                            l.NOT,
                                            zoom=1,
                                            endpts=[xx.end, [xx.end[0] + 3, xx.end[1]]],
                                            botlabel=gate[1],
                                            fill=col_map[color],
                                            toplabel=delay,
                                        )
                                        color += 1
                                G5 = d.add(e.LINE, d='right', xy=not_gate.out)

                            elif len(gate) == 3:
                                delay = Delay(gate[0], gate[2], gate[1])
                                if k == 0:
                                    G4 = d.add(e.LINE, d='right', toplabel=gate[0], xy=[G1.start[0], G1.end[1] - j - 1])
                                    G4 = d.add(e.LINE, d='right', l=2.5, xy=G4.end)
                                else:
                                    G4 = d.add(e.LINE, d='right', toplabel=gate[0], xy=G5.end, l=1.5)

                                if len(circuits[i]) == 3:
                                    if k == len(all_gates) - 1:
                                        nor_color = 0
                                        norx = d.add(l.NOR2, anchor='in2', zoom=1, botlabel=gate[2], xy=G4.end, fill=use[nor_color][2], toplabel=delay)
                                        nor_color -= 1
                                    else:
                                        norx = d.add(l.NOR2, anchor='in2', zoom=1, botlabel=gate[2], xy=G4.end, fill=col_map[color + 1], toplabel=delay)
                                    G5 = d.add(e.LINE, xy=norx.out, d='right')
                                    G7 = d.add(e.LINE, xy=norx.in1, d='left', label=gate[1], l=1.3)
                                    up_key = d.add(e.LINE, xy=G7.end, d='up')
                                    use.append((gate[1], up_key, col_map[color]))
                                    color += 1

                                else:
                                    if k == len(all_gates) - 1:
                                        norx = d.add(l.NOR2, anchor='in1', zoom=1, botlabel=gate[2], xy=G4.end, fill=use[nor_color][2], toplabel=delay)
                                    else:
                                        norx = d.add(l.NOR2, anchor='in1', zoom=1, botlabel=gate[2], xy=G4.end, fill=col_map[color + 1], toplabel=delay)
                                    G5 = d.add(e.LINE, xy=norx.out, d='right')
                                    G7 = d.add(e.LINE, xy=norx.in2, d='left', label=gate[1], l=1.3)
                                    down_key = d.add(e.LINE, xy=G7.end, d='down')
                                    use.append((gate[1], down_key, col_map[color]))
                                    color += 1

                        last_gate = all_gates[-1].split('-> ')
                        if len(circuits[i]) == 3 and j == 2 and last_gate[1][1:-1] in circuits[i][1]:
                            d.add(e.LINE, endpts=[G5.end, [use[-1][1].end[0], G5.end[1]]])
                            d.add(e.LINE, d='down', endpts=[[use[-1][1].end[0], G5.end[1]], use[-1][1].end])
                            use.pop()

                        for z in range(len(use)):
                            if last_gate[-1][1:-1] == use[z][0][1:]:
                                d.add(e.LINE, endpts=[G5.end, [use[z][1].end[0], G5.end[1]]])
                                d.add(e.LINE, d='up', endpts=[[use[z][1].end[0], G5.end[1]], use[z][1].end])

                if G4 == 0:
                    G4 = G1
                base_promoters = baseList()
                for z in range(len(use)):
                    if use[z][0] in base_promoters:
                        G4 = d.add(e.LINE, d='right', toplabel=use[z][0], xy=[G1.start[0], G4.start[1] - 2])
                        d.add(e.LINE, d='right', endpts=[G4.end, [use[z][1].end[0], G4.start[1]]])
                        d.add(e.LINE, xy=G4.end, d='up', endpts=[[use[z][1].end[0], G4.start[1]], use[z][1].end])

                d.draw()
                d.save(str(USER_FILES_DIR / ('Circuit ' + str(file_num) + ' Logic.png')), dpi=300)


if __name__ == '__main__':
    logic = Logical_Representation(1000, 1000, 0, 1000)
