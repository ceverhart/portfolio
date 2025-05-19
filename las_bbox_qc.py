from pathlib import Path
import laspy
import geopandas
from shapely import box

def get_header(las_path):
    las_file = laspy.open(las_path)
    return las_file.header

if __name__ == "__main__":
    while True:
        las_path = Path(input("Enter path to LAS/LAZ files: "))
        if las_path.exists():
            print(f"Path: {las_path}")
            break
        else:
            print("Invalid folder path.")

    # Sample set of output fields
    header_fields = ['z_max', 'z_min', 'point_count', \
                     'point_format', 'major_version', \
                     'minor_version', 'creation_date', \
                     'file_source_id', 'generating_software']

    # Create a shell for the header data 
    header_data = {'filename':[],'geometry':[], 'crs':[], 'vdatum':[]}
    for field in header_fields:
        header_data[field] = []

    # Get path for each LAS/Z files
    las_files = list(las_path.glob('*.la[z,s]'))
    las_count = len(las_files)
    if las_count == 0:
        print("No LAS/LAZ files found in this folder")
        raise SystemExit()
    else:
        print(f"Processing {las_count} files")

    # Iterate the list of paths, add field values to dictionary 
    for las in las_files:
        las_header = get_header(las)

        # Include the file name for output
        header_data['filename'].append(las.name)

        for field_name in header_fields:
            header_val = getattr(las_header,field_name)

            if field_name in header_data.keys():
                header_data[field_name].append(header_val)

        # Get the min/max x and y, buid the geometry
        mins = las_header.mins
        maxs = las_header.maxs
        bound_coords = {'minx': mins[0].item(), 'miny': mins[1].item(), \
                        'maxx': maxs[0].item(),'maxy': maxs[1].item()}
        minx = bound_coords['minx']
        miny = bound_coords['miny']
        maxx = bound_coords['maxx']
        maxy = bound_coords['maxy']
        
        # Build shapely box geometry
        bbox_geom = box(minx, miny, maxx, maxy, ccw=True)

        # Add geometry to header data
        header_data['geometry'].append(bbox_geom)
        
        epsg_h = None
        epsg_v = None
        # Get LAS/Z coordinate system and vertical datum
        header_srs = las_header.parse_crs()
        for crs_sub in header_srs.sub_crs_list:
            if crs_sub.is_projected:
                epsg_h = header_srs.sub_crs_list[0].to_epsg()
            elif crs_sub.is_vertical:
                epsg_v = header_srs.sub_crs_list[1].to_epsg()
            elif crs_sub.is_geographic:
                epsg_h = header_srs.sub_crs_list[0].to_epsg()

        header_data['crs'].append(str(epsg_h))
        header_data['vdatum'].append(str(epsg_v))

        # Note: this will assign the last found crs to output
        # Potential improvement opportunity
        epsg = f"EPSG:{epsg_h}"

    # Output GeoDataFrame
    gdf_out = geopandas.GeoDataFrame(header_data, \
                                         geometry='geometry', crs=epsg)

    out_path = las_path.joinpath('las_bbox_qc.shp')

    # Write the output
    try:
        gdf_out.to_file(out_path)
    except PermissionError as perm_error:
        print("Unable to overwrite. Is it open in another application?")
    
