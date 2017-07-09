import hashlib
import os
import time
import random


def read_voxlyze_results(population, print_log, filename="softbotsOutput.xml"):
    i = 0
    max_attempts = 60
    file_size = 0
    this_file = ""

    while (i < max_attempts) and (file_size == 0):
        try:
            file_size = os.stat(filename).st_size
            this_file = open(filename)
        except ImportError:  # TODO: is this the correct exception?
            file_size = 0
        i += 1
        time.sleep(1)

    if file_size == 0:
        print_log.message("ERROR: Cannot find a non-empty fitness file in %d attempts: abort" % max_attempts)
        exit(1)

    results = {rank: None for rank in range(len(population.objective_dict))}
    for rank, details in population.objective_dict.items():
        this_file = open(filename)  # TODO: is there a way to just go back to the first line without reopening the file?
        tag = details["tag"]
        if tag is not None:
            for line in this_file:
                if tag in line:
                    results[rank] = float(line[line.find(tag) + len(tag):line.find("</" + tag[1:])])

    return results


def write_voxelyze_file(sim, env, individual, run_directory, run_name):

    # TODO: work in base.py to remove redundant static text in this function

    # obstacles: the following is used to freeze any elements not apart of the individual
    body_xlim = (0, individual.genotype.orig_size_xyz[0])
    body_ylim = (0, individual.genotype.orig_size_xyz[1])  # todo: if starting ind somewhere besides (0, 0)
    body_zlim = ((env.hurdle_height+1), individual.genotype.orig_size_xyz[2]+(env.hurdle_height+1))

    padding = env.num_hurdles * (env.space_between_hurdles + 1)
    x_pad = [padding, padding]
    y_pad = [padding, padding]

    if not env.circular_hurdles and env.num_hurdles > 0:
        if env.num_hurdles == 1:  # single hurdle
            y_pad = x_pad = [env.space_between_hurdles/2+1, env.space_between_hurdles/2+1]
        else:  # tunnel
            x_pad = [env.tunnel_width/2, env.tunnel_width/2]
            y_pad[0] = max(env.space_between_hurdles, body_ylim[1]-1) + 1 - body_ylim[1] + body_ylim[0]

    if env.forward_hurdles_only and env.num_hurdles > 0:  # ring
        y_pad[0] = body_ylim[1]

    if env.needle_position > 0:
        y_pad = x_pad = [0, env.needle_position]

    workspace_xlim = (-x_pad[0], body_xlim[1] + x_pad[1])
    workspace_ylim = (-y_pad[0], body_ylim[1] + y_pad[1])
    workspace_zlim = (0, max(env.wall_height, body_zlim[1]))

    length_workspace_xyz = (float(workspace_xlim[1]-workspace_xlim[0]),
                            float(workspace_ylim[1]-workspace_ylim[0]),
                            float(workspace_zlim[1]-workspace_zlim[0]))

    fixed_regions_dict = {key: {"X": {}, "Y": {}, "dX": {}, "dY": {}} for key in range(4)}

    fixed_regions_dict[0] = {"X": 0, "dX": (x_pad[0]-1)/length_workspace_xyz[0]}

    fixed_regions_dict[1] = {"X": (body_xlim[1]-body_xlim[0]+x_pad[0]+1)/length_workspace_xyz[0],
                             "dX": 1 - (body_xlim[1]-body_xlim[0]+x_pad[0]+1)/length_workspace_xyz[0]}

    fixed_regions_dict[2] = {"Y": 0, "dY": (y_pad[0]-1)/length_workspace_xyz[1]}

    fixed_regions_dict[3] = {"Y": (body_ylim[1]-body_ylim[0]+y_pad[0]+1)/length_workspace_xyz[1],
                             "dY": 1 - (body_ylim[1]-body_ylim[0]+y_pad[0]+1)/length_workspace_xyz[1]}

    # update any env variables based on outputs instead of writing outputs in
    for name, details in individual.genotype.to_phenotype_mapping.items():
        if details["env_kws"] is not None:
            for env_key, env_func in details["env_kws"].items():
                setattr(env, env_key, env_func(details["state"]))  # currently only used when evolving frequency
                # print env_key, env_func(details["state"])

    voxelyze_file = open(run_directory + "/voxelyzeFiles/" + run_name + "--id_%05i.vxa" % individual.id, "w")

    voxelyze_file.write(
        "<?xml version=\"1.0\" encoding=\"ISO-8859-1\"?>\n\
        <VXA Version=\"1.0\">\n\
        <Simulator>\n")

    # Sim
    for name, tag in sim.new_param_tag_dict.items():
        voxelyze_file.write(tag + str(getattr(sim, name)) + "</" + tag[1:] + "\n")

    voxelyze_file.write(
        "<Integration>\n\
        <Integrator>0</Integrator>\n\
        <DtFrac>" + str(sim.dt_frac) + "</DtFrac>\n\
        </Integration>\n\
        <Damping>\n\
        <BondDampingZ>1</BondDampingZ>\n\
        <ColDampingZ>0.8</ColDampingZ>\n\
        <SlowDampingZ>0.01</SlowDampingZ>\n\
        </Damping>\n\
        <Collisions>\n\
        <SelfColEnabled>" + str(int(sim.self_collisions_enabled)) + "</SelfColEnabled>\n\
        <ColSystem>3</ColSystem>\n\
        <CollisionHorizon>2</CollisionHorizon>\n\
        </Collisions>\n\
        <Features>\n\
        <FluidDampEnabled>0</FluidDampEnabled>\n\
        <PoissonKickBackEnabled>0</PoissonKickBackEnabled>\n\
        <EnforceLatticeEnabled>0</EnforceLatticeEnabled>\n\
        </Features>\n\
        <SurfMesh>\n\
        <CMesh>\n\
        <DrawSmooth>1</DrawSmooth>\n\
        <Vertices/>\n\
        <Facets/>\n\
        <Lines/>\n\
        </CMesh>\n\
        </SurfMesh>\n\
        <StopCondition>\n\
        <StopConditionType>" + str(int(sim.stop_condition)) + "</StopConditionType>\n\
        <StopConditionValue>" + str(sim.simulation_time) + "</StopConditionValue>\n\
        <AfterlifeTime>" + str(sim.afterlife_time) + "</AfterlifeTime>\n\
        <MidLifeFreezeTime>" + str(sim.mid_life_freeze_time) + "</MidLifeFreezeTime>\n\
        <InitCmTime>" + str(sim.fitness_eval_init_time) + "</InitCmTime>\n\
        </StopCondition>\n\
        <EquilibriumMode>\n\
        <EquilibriumModeEnabled>" + str(sim.equilibrium_mode) + "</EquilibriumModeEnabled>\n\
        </EquilibriumMode>\n\
        <GA>\n\
        <WriteFitnessFile>1</WriteFitnessFile>\n\
        <FitnessFileName>" + run_directory + "/fitnessFiles/softbotsOutput--id_%05i.xml" % individual.id +
        "</FitnessFileName>\n\
        <QhullTmpFile>" + run_directory + "/tempFiles/qhullInput--id_%05i.txt" % individual.id + "</QhullTmpFile>\n\
        <CurvaturesTmpFile>" + run_directory + "/tempFiles/curvatures--id_%05i.txt" % individual.id +
        "</CurvaturesTmpFile>\n\
        </GA>\n\
        <MinTempFact>" + str(sim.min_temp_fact) + "</MinTempFact>\n\
        <MaxTempFactChange>" + str(sim.max_temp_fact_change) + "</MaxTempFactChange>\n\
        <MaxStiffnessChange>" + str(sim.max_stiffness_change) + "</MaxStiffnessChange>\n\
        <MinElasticMod>" + str(sim.min_elastic_mod) + "</MinElasticMod>\n\
        <MaxElasticMod>" + str(sim.max_elastic_mod) + "</MaxElasticMod>\n\
        <ErrorThreshold>" + str(0) + "</ErrorThreshold>\n\
        <ThresholdTime>" + str(0) + "</ThresholdTime>\n\
        <MaxKP>" + str(0) + "</MaxKP>\n\
        <MaxKI>" + str(0) + "</MaxKI>\n\
        <MaxANTIWINDUP>" + str(0) + "</MaxANTIWINDUP>\n")

    if hasattr(individual, "parent_lifetime"):
        if individual.parent_lifetime > 0:
            voxelyze_file.write("<ParentLifetime>" + str(individual.parent_lifetime) + "</ParentLifetime>\n")
        elif individual.lifetime > 0:
            voxelyze_file.write("<ParentLifetime>" + str(individual.lifetime) + "</ParentLifetime>\n")

    voxelyze_file.write("</Simulator>\n")

    # Env
    voxelyze_file.write(
        "<Environment>\n")
    for name, tag in env.new_param_tag_dict.items():
        voxelyze_file.write(tag + str(getattr(env, name)) + "</" + tag[1:] + "\n")

    if env.num_hurdles > 0:
        voxelyze_file.write(
            "<Boundary_Conditions>\n\
            <NumBCs>5</NumBCs>\n\
            <FRegion>\n\
            <PrimType>0</PrimType>\n\
            <X>" + str(fixed_regions_dict[0]["X"]) + "</X>\n\
            <Y>0</Y>\n\
            <Z>0</Z>\n\
            <dX>" + str(fixed_regions_dict[0]["dX"]) + "</dX>\n\
            <dY>1</dY>\n\
            <dZ>1</dZ>\n\
            <Radius>0</Radius>\n\
            <R>0.4</R>\n\
            <G>0.6</G>\n\
            <B>0.4</B>\n\
            <alpha>1</alpha>\n\
            <DofFixed>63</DofFixed>\n\
            <ForceX>0</ForceX>\n\
            <ForceY>0</ForceY>\n\
            <ForceZ>0</ForceZ>\n\
            <TorqueX>0</TorqueX>\n\
            <TorqueY>0</TorqueY>\n\
            <TorqueZ>0</TorqueZ>\n\
            <DisplaceX>0</DisplaceX>\n\
            <DisplaceY>0</DisplaceY>\n\
            <DisplaceZ>0</DisplaceZ>\n\
            <AngDisplaceX>0</AngDisplaceX>\n\
            <AngDisplaceY>0</AngDisplaceY>\n\
            <AngDisplaceZ>0</AngDisplaceZ>\n\
            </FRegion>\n\
            <FRegion>\n\
            <PrimType>0</PrimType>\n\
            <X>" + str(fixed_regions_dict[1]["X"]) + "</X>\n\
            <Y>0</Y>\n\
            <Z>0</Z>\n\
            <dX>" + str(fixed_regions_dict[1]["dX"]) + "</dX>\n\
            <dY>1</dY>\n\
            <dZ>1</dZ>\n\
            <Radius>0</Radius>\n\
            <R>0.4</R>\n\
            <G>0.6</G>\n\
            <B>0.4</B>\n\
            <alpha>1</alpha>\n\
            <DofFixed>63</DofFixed>\n\
            <ForceX>0</ForceX>\n\
            <ForceY>0</ForceY>\n\
            <ForceZ>0</ForceZ>\n\
            <TorqueX>0</TorqueX>\n\
            <TorqueY>0</TorqueY>\n\
            <TorqueZ>0</TorqueZ>\n\
            <DisplaceX>0</DisplaceX>\n\
            <DisplaceY>0</DisplaceY>\n\
            <DisplaceZ>0</DisplaceZ>\n\
            <AngDisplaceX>0</AngDisplaceX>\n\
            <AngDisplaceY>0</AngDisplaceY>\n\
            <AngDisplaceZ>0</AngDisplaceZ>\n\
            </FRegion>\n\
            <FRegion>\n\
            <PrimType>0</PrimType>\n\
            <X>0</X>\n\
            <Y>" + str(fixed_regions_dict[2]["Y"]) + "</Y>\n\
            <Z>0</Z>\n\
            <dX>1</dX>\n\
            <dY>" + str(fixed_regions_dict[2]["dY"]) + "</dY>\n\
            <dZ>1</dZ>\n\
            <Radius>0</Radius>\n\
            <R>0.4</R>\n\
            <G>0.6</G>\n\
            <B>0.4</B>\n\
            <alpha>1</alpha>\n\
            <DofFixed>63</DofFixed>\n\
            <ForceX>0</ForceX>\n\
            <ForceY>0</ForceY>\n\
            <ForceZ>0</ForceZ>\n\
            <TorqueX>0</TorqueX>\n\
            <TorqueY>0</TorqueY>\n\
            <TorqueZ>0</TorqueZ>\n\
            <DisplaceX>0</DisplaceX>\n\
            <DisplaceY>0</DisplaceY>\n\
            <DisplaceZ>0</DisplaceZ>\n\
            <AngDisplaceX>0</AngDisplaceX>\n\
            <AngDisplaceY>0</AngDisplaceY>\n\
            <AngDisplaceZ>0</AngDisplaceZ>\n\
            </FRegion>\n\
            <FRegion>\n\
            <PrimType>0</PrimType>\n\
            <X>0</X>\n\
            <Y>" + str(fixed_regions_dict[3]["Y"]) + "</Y>\n\
            <Z>0</Z>\n\
            <dX>1</dX>\n\
            <dY>" + str(fixed_regions_dict[3]["dY"]) + "</dY>\n\
            <dZ>1</dZ>\n\
            <Radius>0</Radius>\n\
            <R>0.4</R>\n\
            <G>0.6</G>\n\
            <B>0.4</B>\n\
            <alpha>1</alpha>\n\
            <DofFixed>63</DofFixed>\n\
            <ForceX>0</ForceX>\n\
            <ForceY>0</ForceY>\n\
            <ForceZ>0</ForceZ>\n\
            <TorqueX>0</TorqueX>\n\
            <TorqueY>0</TorqueY>\n\
            <TorqueZ>0</TorqueZ>\n\
            <DisplaceX>0</DisplaceX>\n\
            <DisplaceY>0</DisplaceY>\n\
            <DisplaceZ>0</DisplaceZ>\n\
            <AngDisplaceX>0</AngDisplaceX>\n\
            <AngDisplaceY>0</AngDisplaceY>\n\
            <AngDisplaceZ>0</AngDisplaceZ>\n\
            </FRegion>\n\
            <FRegion>\n\
                <PrimType>0</PrimType>\n\
                <X>0</X>\n\
                <Y>0</Y>\n\
                <Z>0</Z>\n\
                <dX>1</dX>\n\
                <dY>1</dY>\n\
                <dZ>" + str(env.hurdle_height/length_workspace_xyz[2]) + "</dZ>\n\
                <Radius>0</Radius>\n\
                <R>0.4</R>\n\
                <G>0.6</G>\n\
                <B>0.4</B>\n\
                <alpha>1</alpha>\n\
                <DofFixed>63</DofFixed>\n\
                <ForceX>0</ForceX>\n\
                <ForceY>0</ForceY>\n\
                <ForceZ>0</ForceZ>\n\
                <TorqueX>0</TorqueX>\n\
                <TorqueY>0</TorqueY>\n\
                <TorqueZ>0</TorqueZ>\n\
                <DisplaceX>0</DisplaceX>\n\
                <DisplaceY>0</DisplaceY>\n\
                <DisplaceZ>0</DisplaceZ>\n\
                <AngDisplaceX>0</AngDisplaceX>\n\
                <AngDisplaceY>0</AngDisplaceY>\n\
                <AngDisplaceZ>0</AngDisplaceZ>\n\
            </FRegion>\n\
            </Boundary_Conditions>\n"
        )

    else:
        voxelyze_file.write(
            "<Fixed_Regions>\n\
            <NumFixed>0</NumFixed>\n\
            </Fixed_Regions>\n\
            <Forced_Regions>\n\
            <NumForced>0</NumForced>\n\
            </Forced_Regions>\n"
            )

    voxelyze_file.write(
        "<Gravity>\n\
        <GravEnabled>" + str(env.gravity_enabled) + "</GravEnabled>\n\
        <GravAcc>-9.81</GravAcc>\n\
        <FloorEnabled>" + str(env.floor_enabled) + "</FloorEnabled>\n\
        <FloorSlope>" + str(env.floor_slope) + "</FloorSlope>\n\
        </Gravity>\n\
        <Thermal>\n\
        <TempEnabled>" + str(env.temp_enabled) + "</TempEnabled>\n\
        <TempAmp>" + str(env.temp_amp) + "</TempAmp>\n\
        <TempBase>25</TempBase>\n\
        <VaryTempEnabled>1</VaryTempEnabled>\n\
        <TempPeriod>" + str(1.0 / env.frequency) + "</TempPeriod>\n\
        </Thermal>\n\
        <TimeBetweenTraces>" + str(env.time_between_traces) + "</TimeBetweenTraces>\n\
        <StickyFloor>" + str(env.sticky_floor) + "</StickyFloor>\n\
        <NeedleInHaystack>" + str(int(env.needle_position > 0)) + "</NeedleInHaystack>\n\
        <BallisticSlowdownFact>" + str(env.ballistic_slowdown_fact) + "</BallisticSlowdownFact>\n\
        <MaxSlowdownPermitted>" + str(env.ballistic_max_slowdown) + "</MaxSlowdownPermitted>\n\
        </Environment>\n")

    voxelyze_file.write(
        "<VXC Version=\"0.93\">\n\
        <Lattice>\n\
        <Lattice_Dim>" + str(env.lattice_dimension) + "</Lattice_Dim>\n\
        <X_Dim_Adj>1</X_Dim_Adj>\n\
        <Y_Dim_Adj>1</Y_Dim_Adj>\n\
        <Z_Dim_Adj>1</Z_Dim_Adj>\n\
        <X_Line_Offset>0</X_Line_Offset>\n\
        <Y_Line_Offset>0</Y_Line_Offset>\n\
        <X_Layer_Offset>0</X_Layer_Offset>\n\
        <Y_Layer_Offset>0</Y_Layer_Offset>\n\
        </Lattice>\n\
        <Voxel>\n\
        <Vox_Name>BOX</Vox_Name>\n\
        <X_Squeeze>1</X_Squeeze>\n\
        <Y_Squeeze>1</Y_Squeeze>\n\
        <Z_Squeeze>1</Z_Squeeze>\n\
        </Voxel>\n\
        <Palette>\n\
        <Material ID=\"1\">\n\
            <MatType>0</MatType>\n\
            <Name>Passive_Soft</Name>\n\
            <Display>\n\
            <Red>0</Red>\n\
            <Green>1</Green>\n\
            <Blue>1</Blue>\n\
            <Alpha>1</Alpha>\n\
            </Display>\n\
            <Mechanical>\n\
            <MatModel>0</MatModel>\n\
            <Elastic_Mod>" + str(env.fat_stiffness) + "</Elastic_Mod>\n\
            <Plastic_Mod>0</Plastic_Mod>\n\
            <Yield_Stress>0</Yield_Stress>\n\
            <FailModel>0</FailModel>\n\
            <Fail_Stress>0</Fail_Stress>\n\
            <Fail_Strain>0</Fail_Strain>\n\
            <Density>1e+006</Density>\n\
            <Poissons_Ratio>0.35</Poissons_Ratio>\n\
            <CTE>0</CTE>\n\
            <uStatic>1</uStatic>\n\
            <uDynamic>0.5</uDynamic>\n\
            </Mechanical>\n\
        </Material>\n\
        <Material ID=\"2\">\n\
            <MatType>0</MatType>\n\
            <Name>Passive_Hard</Name>\n\
            <Display>\n\
            <Red>0</Red>\n\
            <Green>0</Green>\n\
            <Blue>1</Blue>\n\
            <Alpha>1</Alpha>\n\
            </Display>\n\
            <Mechanical>\n\
            <MatModel>0</MatModel>\n\
            <Elastic_Mod>" + str(env.bone_stiffness) + "</Elastic_Mod>\n\
            <Plastic_Mod>0</Plastic_Mod>\n\
            <Yield_Stress>0</Yield_Stress>\n\
            <FailModel>0</FailModel>\n\
            <Fail_Stress>0</Fail_Stress>\n\
            <Fail_Strain>0</Fail_Strain>\n\
            <Density>1e+006</Density>\n\
            <Poissons_Ratio>0.35</Poissons_Ratio>\n\
            <CTE>0</CTE>\n\
            <uStatic>1</uStatic>\n\
            <uDynamic>0.5</uDynamic>\n\
            </Mechanical>\n\
        </Material>\n\
            <Material ID=\"3\">\n\
            <MatType>0</MatType>\n\
            <Name>Active_+</Name>\n\
            <Display>\n\
            <Red>1</Red>\n\
            <Green>0</Green>\n\
            <Blue>0</Blue>\n\
            <Alpha>1</Alpha>\n\
            </Display>\n\
            <Mechanical>\n\
            <MatModel>0</MatModel>\n\
            <Elastic_Mod>" + str(env.muscle_stiffness) + "</Elastic_Mod>\n\
            <Plastic_Mod>0</Plastic_Mod>\n\
            <Yield_Stress>0</Yield_Stress>\n\
            <FailModel>0</FailModel>\n\
            <Fail_Stress>0</Fail_Stress>\n\
            <Fail_Strain>0</Fail_Strain>\n\
            <Density>1e+006</Density>\n\
            <Poissons_Ratio>0.35</Poissons_Ratio>\n\
            <CTE>" + str(0.01*(1+random.uniform(0, env.actuation_variance))) + "</CTE>\n\
            <uStatic>1</uStatic>\n\
            <uDynamic>0.5</uDynamic>\n\
            </Mechanical>\n\
        </Material>\n\
        <Material ID=\"4\">\n\
            <MatType>0</MatType>\n\
            <Name>Active_-</Name>\n\
            <Display>\n\
            <Red>0</Red>\n\
            <Green>1</Green>\n\
            <Blue>0</Blue>\n\
            <Alpha>1</Alpha>\n\
            </Display>\n\
            <Mechanical>\n\
            <MatModel>0</MatModel>\n\
            <Elastic_Mod>" + str(env.muscle_stiffness) + "</Elastic_Mod>\n\
            <Plastic_Mod>0</Plastic_Mod>\n\
            <Yield_Stress>0</Yield_Stress>\n\
            <FailModel>0</FailModel>\n\
            <Fail_Stress>0</Fail_Stress>\n\
            <Fail_Strain>0</Fail_Strain>\n\
            <Density>1e+006</Density>\n\
            <Poissons_Ratio>0.35</Poissons_Ratio>\n\
            <CTE>" + str(-0.01*(1+random.uniform(0, env.actuation_variance))) + "</CTE>\n\
            <uStatic>1</uStatic>\n\
            <uDynamic>0.5</uDynamic>\n\
            </Mechanical>\n\
        </Material>\n\
        <Material ID=\"5\">\n\
            <MatType>0</MatType>\n\
            <Name>Obstacle</Name>\n\
            <Display>\n\
            <Red>1</Red>\n\
            <Green>0.784</Green>\n\
            <Blue>0</Blue>\n\
            <Alpha>1</Alpha>\n\
            </Display>\n\
            <Mechanical>\n\
            <MatModel>0</MatModel>\n\
            <Elastic_Mod>5e+007</Elastic_Mod>\n\
            <Plastic_Mod>0</Plastic_Mod>\n\
            <Yield_Stress>0</Yield_Stress>\n\
            <FailModel>0</FailModel>\n\
            <Fail_Stress>0</Fail_Stress>\n\
            <Fail_Strain>0</Fail_Strain>\n\
            <Density>1e+006</Density>\n\
            <Poissons_Ratio>0.35</Poissons_Ratio>\n\
            <CTE>0</CTE>\n\
            <uStatic>1</uStatic>\n\
            <uDynamic>0.5</uDynamic>\n\
            </Mechanical>\n\
        </Material>\n\
        <Material ID=\"6\">\n\
            <MatType>0</MatType>\n\
            <Name>Head_Active_+</Name>\n\
            <Display>\n\
            <Red>1</Red>\n\
            <Green>1</Green>\n\
            <Blue>0</Blue>\n\
            <Alpha>1</Alpha>\n\
            </Display>\n\
            <Mechanical>\n\
            <MatModel>0</MatModel>\n\
            <Elastic_Mod>" + str(env.fat_stiffness) + "</Elastic_Mod>\n\
            <Plastic_Mod>0</Plastic_Mod>\n\
            <Yield_Stress>0</Yield_Stress>\n\
            <FailModel>0</FailModel>\n\
            <Fail_Stress>0</Fail_Stress>\n\
            <Fail_Strain>0</Fail_Strain>\n\
            <Density>1e+006</Density>\n\
            <Poissons_Ratio>0.35</Poissons_Ratio>\n\
            <CTE>" + str(0.01 * (1 + random.uniform(0, env.actuation_variance))) + "</CTE>\n\
            <uStatic>1</uStatic>\n\
            <uDynamic>0.5</uDynamic>\n\
            </Mechanical>\n\
        </Material>\n\
        <Material ID=\"7\">\n\
            <MatType>0</MatType>\n\
            <Name>Food</Name>\n\
            <Display>\n\
            <Red>1</Red>\n\
            <Green>1</Green>\n\
            <Blue>0</Blue>\n\
            <Alpha>1</Alpha>\n\
            </Display>\n\
            <Mechanical>\n\
            <MatModel>0</MatModel>\n\
            <Elastic_Mod>" + str(env.muscle_stiffness) + "</Elastic_Mod>\n\
            <Plastic_Mod>0</Plastic_Mod>\n\
            <Yield_Stress>0</Yield_Stress>\n\
            <FailModel>0</FailModel>\n\
            <Fail_Stress>0</Fail_Stress>\n\
            <Fail_Strain>0</Fail_Strain>\n\
            <Density>1e+006</Density>\n\
            <Poissons_Ratio>0.35</Poissons_Ratio>\n\
            <CTE>0</CTE>\n\
            <uStatic>1</uStatic>\n\
            <uDynamic>0.5</uDynamic>\n\
            </Mechanical>\n\
        </Material>\n\
        </Palette>\n\
        <Structure Compression=\"ASCII_READABLE\">\n\
        <X_Voxels>" + str(length_workspace_xyz[0]) + "</X_Voxels>\n\
        <Y_Voxels>" + str(length_workspace_xyz[1]) + "</Y_Voxels>\n\
        <Z_Voxels>" + str(length_workspace_xyz[2]) + "</Z_Voxels>\n")

    all_tags = [details["tag"] for name, details in individual.genotype.to_phenotype_mapping.items()]
    if "<Data>" not in all_tags:  # not evolving topology -- fixed presence/absence of voxels
        voxelyze_file.write("<Data>\n")
        for z in range(*workspace_zlim):
            voxelyze_file.write("<Layer><![CDATA[")
            for y in range(*workspace_ylim):
                for x in range(*workspace_xlim):

                    if (body_xlim[0] <= x < body_xlim[1]) and (body_ylim[0] <= y < body_ylim[1]) and (body_zlim[0] <= z < body_zlim[1]):

                        if env.biped and (z < body_zlim[1]*env.biped_leg_proportion) and (x == body_xlim[1]/2):
                            voxelyze_file.write("0")

                        elif z == body_zlim[1]-1:
                            voxelyze_file.write("6")  # head id

                        else:
                            voxelyze_file.write("3")

                    elif env.needle_position > 0:
                        if (x == workspace_xlim[1]-1) and (y == workspace_ylim[1]-1) and (z == 0):
                            voxelyze_file.write("7")  # food
                        else:
                            voxelyze_file.write("0")

                    elif env.num_hurdles > 0:
                        # within the fixed regions
                        xy_centered = [x-body_xlim[1]/2, y-body_ylim[1]/2]
                        is_obstacle = False

                        if env.circular_hurdles:  # rings of circles
                            for hurdle in range(-1, env.num_hurdles + 1):
                                hurdle_radius = hurdle * env.space_between_hurdles
                                if abs(xy_centered[0]**2+xy_centered[1]**2-hurdle_radius**2) <= hurdle_radius:
                                    if z < env.hurdle_height:
                                        is_obstacle = True
                                        if env.debris and x % 2 == 0:
                                            is_obstacle = False

                                elif y == workspace_ylim[0] and env.back_stop and abs(xy_centered[0]) >= hurdle_radius/hurdle and abs(xy_centered[0]) <= hurdle_radius:
                                    if z < env.wall_height:
                                        if (env.fence and (x+z) % 2 == 0) or not env.fence:
                                            is_obstacle = True  # back wall

                        else:  # tunnel

                            start = body_ylim[1]*env.squeeze_start
                            end = body_ylim[1]*env.squeeze_end
                            p = (y-start) / float(end-start)

                            adj = 0
                            if y > body_ylim[1]*env.squeeze_start:
                                adj = int(p * env.squeeze_rate)

                            if env.constant_squeeze and y > body_ylim[1]*env.squeeze_end:
                                adj = min(int(env.squeeze_rate), workspace_xlim[1]-body_xlim[1])

                            wall = [workspace_xlim[0] + adj,
                                    workspace_xlim[1] - 1 - adj]

                            if x in wall and z < env.wall_height:
                                if (env.fence and (y+z) % 2 == 0) or not env.fence:
                                    is_obstacle = True  # wall

                            elif y % env.space_between_hurdles == 0 and z < env.hurdle_height:
                                is_obstacle = True  # hurdle
                                if env.debris and y > env.debris_start*body_ylim[1]:
                                    if (y % 2 == 0 and (x+z) % 2 == 0) or (y % 2 == 1 and (x+z) % 2 == 1) or x <= wall[0] + 1 or x >= wall[1] - 1:
                                        is_obstacle = False  # nothing
                                elif x <= wall[0] or x >= wall[1]:
                                    is_obstacle = False  # nothing

                                if y > env.hurdle_stop*body_ylim[1]:
                                    is_obstacle = False

                            if y == workspace_ylim[0] and env.back_stop and z < env.wall_height:
                                if (env.fence and (x+z) % 2 == 0) or not env.fence:
                                    is_obstacle = True  # back wall

                        if is_obstacle:
                            voxelyze_file.write("5")
                        else:
                            voxelyze_file.write("0")  # flat ground

                    else:
                        voxelyze_file.write("0")  # flat ground

            voxelyze_file.write("]]></Layer>\n")
        voxelyze_file.write("</Data>\n")

    # append custom parameters
    string_for_md5 = ""

    for name, details in individual.genotype.to_phenotype_mapping.items():

        # start tag
        if details["env_kws"] is None:
            voxelyze_file.write(details["tag"]+"\n")

        # record any additional params associated with the output
        if details["params"] is not None:
            for param_tag, param in zip(details["param_tags"], details["params"]):
                voxelyze_file.write(param_tag + str(param) + "</" + param_tag[1:] + "\n")

        if details["env_kws"] is None:
            # write the output state matrix to file
            for z in range(*workspace_zlim):
                voxelyze_file.write("<Layer><![CDATA[")
                for y in range(*workspace_ylim):
                    for x in range(*workspace_xlim):

                        if (body_xlim[0] <= x < body_xlim[1]) and (body_ylim[0] <= y < body_ylim[1]) and (body_zlim[0] <= z < body_zlim[1]):
                            if individual.age == 0 and details["age_zero_overwrite"] is not None:
                                state = details["age_zero_overwrite"]

                            elif details["switch_proportion"] > 0 and (x < body_xlim[1]-details["switch_proportion"]):
                                # this is like the 'inverse' switch- if true then not switch and equal to other net
                                switch_net_key = details["switch_name"]
                                switch_net = individual.genotype.to_phenotype_mapping[switch_net_key]
                                state = details["output_type"](switch_net["state"][x-body_xlim[0], y-body_ylim[0], z-(env.hurdle_height+1)])

                            else:
                                state = details["output_type"](details["state"][x-body_xlim[0], y-body_ylim[0], z-(env.hurdle_height+1)])

                        # elif (env.needle_position > 0) and (x == workspace_xlim[1] - 1) and (y == workspace_ylim[1] - 1) and (z == 0):
                        #     state = -1  # tiny food

                        elif env.circular_hurdles and z < env.hurdle_height and env.debris and x % 2 != 0:
                            state = 0
                            xy_centered = [x-body_xlim[1]/2, y-body_ylim[1]/2]
                            for hurdle in range(1, env.num_hurdles + 1):
                                hurdle_radius = hurdle * env.space_between_hurdles
                                if abs(xy_centered[0]**2 + xy_centered[1]**2 - hurdle_radius**2) <= hurdle_radius:
                                    state = -1  # tiny debris

                        elif env.num_hurdles > 0 and z < env.hurdle_height and workspace_xlim[0] < x < workspace_xlim[1]-1:
                            if env.debris_size < -1:
                                state = 0.5*random.random()-1
                            else:
                                state = env.debris_size  # tiny debris

                        else:
                            state = 0

                        voxelyze_file.write(str(state))
                        if details["tag"] != "<Data>":  # TODO more dynamic
                            voxelyze_file.write(", ")
                        string_for_md5 += str(state)

                voxelyze_file.write("]]></Layer>\n")

        # end tag
        if details["env_kws"] is None:
            voxelyze_file.write("</" + details["tag"][1:] + "\n")

    voxelyze_file.write(
        "</Structure>\n\
        </VXC>\n\
        </VXA>")
    voxelyze_file.close()

    m = hashlib.md5()
    m.update(string_for_md5)

    return m.hexdigest()
