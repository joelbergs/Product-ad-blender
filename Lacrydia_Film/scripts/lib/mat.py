"""Materials (bpy, Cycles): obsidian, glass, coated photo prints, emissive line, screen."""
import bpy


def _new(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    return m, nt


def _out(nt, shader, loc=(600, 0)):
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = loc
    nt.links.new(shader.outputs[0], out.inputs["Surface"])
    return out


def principled(nt, **kw):
    n = nt.nodes.new("ShaderNodeBsdfPrincipled")
    for k, v in kw.items():
        if k in n.inputs:
            n.inputs[k].default_value = v
    return n


def obsidian(name="Obsidian", base=0.003, rough=0.11):
    """Black volcanic glass: deep mirror with a hint of micro-variation so reflections never look like CG."""
    m, nt = _new(name)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 260.0
    noise.inputs["Detail"].default_value = 6.0
    noise.inputs["Roughness"].default_value = 0.6
    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.3
    mr.inputs["From Max"].default_value = 0.7
    mr.inputs["To Min"].default_value = rough * 0.8
    mr.inputs["To Max"].default_value = rough * 1.6
    nt.links.new(noise.outputs["Fac"], mr.inputs["Value"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.004
    bump.inputs["Distance"].default_value = 0.001
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    p = principled(nt, **{"Base Color": (base, base, base * 1.4, 1), "Metallic": 0.0, "Specular IOR Level": 0.6,
                          "IOR": 1.55})
    nt.links.new(mr.outputs["Result"], p.inputs["Roughness"])
    nt.links.new(bump.outputs["Normal"], p.inputs["Normal"])
    # when the floor is seen *via a glossy bounce* (e.g. mirrored in the glass face) it is darkened to ~8%: the glass
    # keeps its clean black reflections while the floor still reflects the object normally for the camera
    lp = nt.nodes.new("ShaderNodeLightPath")
    clampn = nt.nodes.new("ShaderNodeMath")
    clampn.operation = "MINIMUM"
    clampn.inputs[1].default_value = 0.92
    nt.links.new(lp.outputs["Glossy Depth"], clampn.inputs[0])
    dark = nt.nodes.new("ShaderNodeEmission")
    dark.inputs["Color"].default_value = (0, 0, 0, 1)
    mixd = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(clampn.outputs[0], mixd.inputs["Fac"])
    nt.links.new(p.outputs[0], mixd.inputs[1])
    nt.links.new(dark.outputs[0], mixd.inputs[2])
    _out(nt, mixd)
    return m


def glass(name="Glass", ior=1.52, tint=(0.96, 0.985, 1.0), rough=0.0, shadow_transparent=True):
    m, nt = _new(name)
    p = principled(nt, **{"Base Color": (*tint, 1), "Roughness": rough, "IOR": ior, "Transmission Weight": 1.0,
                          "Specular IOR Level": 0.5})
    if shadow_transparent:
        # glass should not cast a hard black shadow: let shadow rays through (a cheap, calm stand-in for caustic light)
        lp = nt.nodes.new("ShaderNodeLightPath")
        tr = nt.nodes.new("ShaderNodeBsdfTransparent")
        mix = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(lp.outputs["Is Shadow Ray"], mix.inputs["Fac"])
        nt.links.new(p.outputs[0], mix.inputs[1])
        nt.links.new(tr.outputs[0], mix.inputs[2])
        _out(nt, mix)
    else:
        _out(nt, p)
    return m


def dark_glass(name="BlackGlass", rough=0.04):
    m, nt = _new(name)
    p = principled(nt, **{"Base Color": (0.004, 0.004, 0.006, 1), "Roughness": rough, "Specular IOR Level": 0.6, "IOR": 1.5})
    _out(nt, p)
    return m


def photo_print(name, image_path, rough=0.32, coat=0.35, emit=0.0, exposure=1.0, diffuse=1.0, spec=0.35):
    """A photographic print under a thin clear coat. `emit` self-illuminates a little so a card is readable in darkness;
    the node 'Gain' is animatable (reveal)."""
    m, nt = _new(name)
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(image_path, check_existing=True)
    tex.image.colorspace_settings.name = "sRGB"
    tex.interpolation = "Cubic"
    tex.extension = "EXTEND"
    gain = nt.nodes.new("ShaderNodeMix")
    gain.data_type = "RGBA"
    gain.blend_type = "MULTIPLY"
    gain.inputs["Factor"].default_value = 1.0
    gain.inputs[7].default_value = (exposure, exposure, exposure, 1)
    nt.links.new(tex.outputs["Color"], gain.inputs[6])
    p = principled(nt, **{"Roughness": rough, "Coat Weight": coat, "Coat Roughness": 0.04, "Specular IOR Level": spec,
                          "Emission Strength": 1.0})
    nt.links.new(gain.outputs[2], p.inputs["Emission Color"])
    p.inputs["Base Color"].default_value = (0.8 * diffuse,) * 3 + (1,)
    if diffuse >= 0.999:
        nt.links.new(gain.outputs[2], p.inputs["Base Color"])
    p.inputs["Emission Strength"].default_value = emit
    # reveal: 0 = the print is in darkness (black), 1 = fully there. Animate m["reveal_node"].outputs[0].
    rev = nt.nodes.new("ShaderNodeValue")
    rev.outputs[0].default_value = 1.0
    black = nt.nodes.new("ShaderNodeEmission")
    black.inputs["Color"].default_value = (0, 0, 0, 1)
    mixr = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(rev.outputs[0], mixr.inputs["Fac"])
    nt.links.new(black.outputs[0], mixr.inputs[1])
    nt.links.new(p.outputs[0], mixr.inputs[2])
    _out(nt, mixr)
    m["gain_node"] = gain.name
    m["bsdf_node"] = p.name
    m["reveal_node"] = rev.name
    return m


def emission(name, color=(1, 1, 1), strength=1.0):
    m, nt = _new(name)
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = (*color, 1)
    e.inputs["Strength"].default_value = strength
    _out(nt, e)
    m["emit_node"] = e.name
    return m


def screen(name, image_path, strength=1.0):
    """Self-lit display: the real app screenshot as emission (sRGB), with a faint glossy layer for glass reflections."""
    m, nt = _new(name)
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(image_path, check_existing=True)
    tex.image.colorspace_settings.name = "sRGB"
    tex.interpolation = "Cubic"
    tex.extension = "EXTEND"
    e = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(tex.outputs["Color"], e.inputs["Color"])
    e.inputs["Strength"].default_value = strength
    _out(nt, e)
    m["emit_node"] = e.name
    return m


def white_ceramic(name="LogoWhite", rough=0.18):
    m, nt = _new(name)
    p = principled(nt, **{"Base Color": (0.92, 0.92, 0.93, 1), "Roughness": rough, "Coat Weight": 0.6,
                          "Coat Roughness": 0.03, "Specular IOR Level": 0.5, "Emission Color": (1, 1, 1, 1),
                          "Emission Strength": 0.0})
    _out(nt, p)
    m["bsdf_node"] = p.name
    return m


def gradient_card(name="ReflCard", peak=1.5, tint=(1.0, 0.99, 0.97), angle=0.0, stops=((0.0, 0.0), (0.55, 0.0), (1.0, 1.0))):
    """Emissive reflection card with a smooth ramp (like a gradient flag): only ever seen as a soft gradient in glass."""
    m, nt = _new(name)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["UV"], sep.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "B_SPLINE"
    el = ramp.color_ramp.elements
    el[0].position, el[0].color = stops[0][0], (stops[0][1],) * 3 + (1,)
    el[1].position, el[1].color = stops[-1][0], (stops[-1][1],) * 3 + (1,)
    for pos, val in stops[1:-1]:
        e = el.new(pos)
        e.color = (val, val, val, 1)
    nt.links.new(sep.outputs["X"], ramp.inputs["Fac"])
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = (*tint, 1)
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    mul.inputs[1].default_value = peak
    nt.links.new(ramp.outputs["Color"], mul.inputs[0])
    nt.links.new(mul.outputs[0], e.inputs["Strength"])
    _out(nt, e)
    m["peak_node"] = mul.name
    return m


def etched_glass(name, mask_path, ior=1.52, tint=(0.96, 0.985, 1.0), frost_rough=0.42, frost_white=0.9):
    """Clear glass with the brand mark acid-etched into the surface (frosted where the mask is white).
    The `amount` Math node scales the mask: animate it to make the mark emerge."""
    m, nt = _new(name)
    clear = principled(nt, **{"Base Color": (*tint, 1), "Roughness": 0.0, "IOR": ior, "Transmission Weight": 1.0,
                              "Specular IOR Level": 0.5})
    frost = principled(nt, **{"Base Color": (frost_white,) * 3 + (1,), "Roughness": frost_rough, "IOR": ior,
                              "Transmission Weight": 0.55, "Specular IOR Level": 0.5, "Coat Weight": 0.0})
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(mask_path, check_existing=True)
    tex.image.colorspace_settings.name = "Non-Color"
    tex.interpolation = "Linear"
    tex.extension = "EXTEND"
    amt = nt.nodes.new("ShaderNodeMath")
    amt.operation = "MULTIPLY"
    amt.inputs[1].default_value = 1.0
    nt.links.new(tex.outputs["Color"], amt.inputs[0])
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(amt.outputs[0], mix.inputs["Fac"])
    nt.links.new(clear.outputs[0], mix.inputs[1])
    nt.links.new(frost.outputs[0], mix.inputs[2])
    lp = nt.nodes.new("ShaderNodeLightPath")
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix2 = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(lp.outputs["Is Shadow Ray"], mix2.inputs["Fac"])
    nt.links.new(mix.outputs[0], mix2.inputs[1])
    nt.links.new(tr.outputs[0], mix2.inputs[2])
    _out(nt, mix2)
    m["amount_node"] = amt.name
    return m


def strip_emitter(name="StripEmit", color=(0.88, 0.94, 1.0), strength=20.0, end_fade=0.30, edge_soft=0.5):
    """Mesh emitter for strip lights: bright core, soft fall-off to both ends and across the width, so the strip's
    reflection in glass/obsidian is a refined streak instead of a hard-edged blown-out block. UV: u = across, v = along."""
    m, nt = _new(name)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["UV"], sep.inputs["Vector"])
    def tri(src, soft, nm):
        # smooth bump: 0 at the ends, 1 across the middle  = smoothstep(|2x-1|)
        a = nt.nodes.new("ShaderNodeMath"); a.operation = "SUBTRACT"; a.inputs[1].default_value = 0.5
        nt.links.new(src, a.inputs[0])
        b = nt.nodes.new("ShaderNodeMath"); b.operation = "ABSOLUTE"
        nt.links.new(a.outputs[0], b.inputs[0])
        mr = nt.nodes.new("ShaderNodeMapRange"); mr.interpolation_type = "SMOOTHSTEP"
        mr.inputs["From Min"].default_value = 0.5
        mr.inputs["From Max"].default_value = 0.5 - soft
        mr.inputs["To Min"].default_value = 0.0
        mr.inputs["To Max"].default_value = 1.0
        nt.links.new(b.outputs[0], mr.inputs["Value"])
        return mr.outputs[0]
    along = tri(sep.outputs["Y"], end_fade, "along")
    across = tri(sep.outputs["X"], edge_soft, "across")
    mul = nt.nodes.new("ShaderNodeMath"); mul.operation = "MULTIPLY"
    nt.links.new(along, mul.inputs[0]); nt.links.new(across, mul.inputs[1])
    mul2 = nt.nodes.new("ShaderNodeMath"); mul2.operation = "MULTIPLY"; mul2.inputs[1].default_value = strength
    nt.links.new(mul.outputs[0], mul2.inputs[0])
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = (*color, 1)
    nt.links.new(mul2.outputs[0], e.inputs["Strength"])
    _out(nt, e)
    m["peak_node"] = mul2.name
    return m
