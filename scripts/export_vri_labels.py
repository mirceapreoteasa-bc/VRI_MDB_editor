#!/usr/bin/env python3
"""Export VRI polygon label strings to a centroid point shapefile."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vri_validator.model import Polygon, load_dataset, text, to_float, to_int

DEFAULT_DRIVER = Path.home() / ".local" / "lib" / "odbc" / "libmdbodbc.so"


def number(value: float | None, decimals: int = 0) -> str:
    if value is None:
        return ""
    if decimals:
        return f"{value:.{decimals}f}"
    return f"{value:g}"


def label_layer(poly: Polygon, level: str | None):
    layers = poly.live_layers()
    if level:
        for layer in layers:
            if text(layer.level) == level:
                return layer
        return None
    for layer in layers:
        if text(layer.level) == "1":
            return layer
    return layers[0] if layers else None


def top_label(layer) -> str:
    if layer is None:
        return ""
    row = layer.row
    return (
        f"CC= {number(to_float(row.get('CROWN_CLOSURE_PCT')))} , "
        f"basal area= {number(to_float(row.get('BASAL_AREA')))}, "
        f"density= {number(to_float(row.get('VRI_LIVE_STEMS_PER_HA')))}"
    )


def sorted_species(layer) -> list[dict[str, str]]:
    if layer is None:
        return []
    return sorted(
        layer.species,
        key=lambda sp: (
            -(to_float(sp.get("SPECIES_PCT")) or 0.0),
            text(sp.get("TREE_SPECIES_CODE")),
        ),
    )


def species_label(layer, limit: int) -> str:
    parts = []
    for sp in sorted_species(layer)[:limit]:
        code = text(sp.get("TREE_SPECIES_CODE"))
        pct = to_float(sp.get("SPECIES_PCT"))
        parts.append(f"{code} {number(pct)}".strip())
    return " ".join(parts)


def age_height_label(layer, limit: int) -> str:
    parts = []
    for sp in sorted_species(layer):
        code = text(sp.get("TREE_SPECIES_CODE"))
        age = to_float(sp.get("AGE"))
        height = to_float(sp.get("HEIGHT"))
        if not code or age is None or height is None:
            continue
        parts.append(f"{code} {number(age)} years / {number(height, 1)} m")
        if len(parts) >= limit:
            break
    return ", ".join(parts)


def build_labels(
    mdb: str,
    output: str,
    epsg: int | None,
    layer_level: str | None,
    max_species: int,
    max_age_species: int,
    include_unclassified: bool,
    id_field: str,
) -> int:
    from osgeo import ogr, osr

    ogr.UseExceptions()

    if not os.environ.get("MDBDRIVER_PATH") and DEFAULT_DRIVER.exists():
        os.environ["MDBDRIVER_PATH"] = str(DEFAULT_DRIVER)

    dataset = load_dataset(mdb)
    by_id = {str(poly.fid): poly for poly in dataset.polygons}

    source = ogr.Open(mdb)
    if source is None:
        raise SystemExit(f"cannot open {mdb}")
    source_layer = source.GetLayerByName("FOREST_COVER_OBJECT")
    if source_layer is None:
        raise SystemExit("FOREST_COVER_OBJECT not found")

    source_srs = source_layer.GetSpatialRef()
    target_srs = osr.SpatialReference()
    if epsg:
        target_srs.ImportFromEPSG(epsg)
    elif source_srs is not None:
        target_srs = source_srs.Clone()
    else:
        target_srs.ImportFromEPSG(3005)
    target_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)

    transform = None
    if source_srs is not None:
        source_srs = source_srs.Clone()
        source_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        transform = osr.CoordinateTransformation(source_srs, target_srs)

    driver = ogr.GetDriverByName("ESRI Shapefile")
    out_path = Path(output)
    for suffix in (".shp", ".shx", ".dbf", ".prj", ".cpg"):
        candidate = out_path.with_suffix(suffix)
        if candidate.exists():
            candidate.unlink()
    out_source = driver.CreateDataSource(str(out_path))
    if out_source is None:
        raise SystemExit(f"cannot create {out_path}")
    out_layer = out_source.CreateLayer(
        out_path.stem, target_srs, ogr.wkbPoint, options=["ENCODING=UTF-8"]
    )
    fco_field = ogr.FieldDefn("FCO_ID", ogr.OFTInteger)
    out_layer.CreateField(fco_field)
    for name, width in (
        ("POLY_NUM", 16),
        ("LAYER", 4),
        ("LBL1", 254),
        ("LBL2", 254),
        ("LBL3", 254),
    ):
        field = ogr.FieldDefn(name, ogr.OFTString)
        field.SetWidth(width)
        out_layer.CreateField(field)

    written = 0
    for feature in source_layer:
        fid = text(feature.GetField(id_field))
        poly = by_id.get(fid)
        if poly is None:
            continue
        bclcs = text((poly.vcpe or {}).get("BCLCS_LEVEL1_CODE"))
        if not include_unclassified and bclcs == "U":
            continue
        geometry = feature.GetGeometryRef()
        if geometry is None:
            continue
        centroid = geometry.PointOnSurface()
        if centroid is None:
            centroid = geometry.Centroid()
        if centroid is None:
            continue
        if transform is not None:
            centroid.Transform(transform)

        layer = label_layer(poly, layer_level)
        out_feature = ogr.Feature(out_layer.GetLayerDefn())
        out_feature.SetField("FCO_ID", int(fid))
        out_feature.SetField("POLY_NUM", poly.number)
        out_feature.SetField("LAYER", text(layer.level) if layer else "")
        out_feature.SetField("LBL1", top_label(layer)[:254])
        out_feature.SetField("LBL2", species_label(layer, max_species)[:254])
        out_feature.SetField("LBL3", age_height_label(layer, max_age_species)[:254])
        out_feature.SetGeometry(centroid)
        out_layer.CreateFeature(out_feature)
        out_feature = None
        written += 1

    out_source = None
    source = None
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mdb", help="input VRI/VRIMS .mdb")
    parser.add_argument("output", help="output centroid point shapefile")
    parser.add_argument("--epsg", type=int, help="output EPSG code (default: source CRS)")
    parser.add_argument("--layer-level", help="tree layer level to label (default: live layer 1)")
    parser.add_argument("--max-species", type=int, default=3)
    parser.add_argument("--max-age-species", type=int, default=2)
    parser.add_argument("--include-unclassified", action="store_true")
    parser.add_argument("--id-field", default="FOREST_COVER_OBJECT_ID")
    args = parser.parse_args()

    written = build_labels(
        args.mdb,
        args.output,
        args.epsg,
        args.layer_level,
        args.max_species,
        args.max_age_species,
        args.include_unclassified,
        args.id_field,
    )
    print(f"Wrote {written} label points to {args.output}")


if __name__ == "__main__":
    main()
