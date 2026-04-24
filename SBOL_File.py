from sbol2 import *
from functions import *
import pandas as pd

class SBOL_File:
    def __init__(self, total_gates, total_time, option, num):
        DeleteExistingFiles()
        circuits = ReadFile()
        Component_strings = self.ListOfLines(circuits)
        self.geneticPartsDf = None #dataframe containing information of genetic parts such as DNA sequence
        self.gateRBS = {} #gets rbs corresponding to the gate
        #read genetic parts file, import sequences and also create GATE-RBS mapping
        self.readGeneticParts()
        self.gateRBSMapping()
        self.CreateFile(Component_strings, len(Component_strings), total_gates, total_time, option, num)

    def readGeneticParts(self):
        """
        This function loads the csv file genetic_parts.csv into a
        pandas dataframe for better access when adding sequences
        """
        self.geneticPartsDf = pd.read_csv(GENETIC_PARTS_FILE)


    def gateRBSMapping(self):
        """
        This function creates a mapping between a gate and it's corresponding
        RBS (AmeR is mappedd to A1, PhlF mapped to P1, and so on) as given in the
        genetic_parts.csv file
        """
        listGates = self.geneticPartsDf.loc[self.geneticPartsDf.type == "CDS"].part
        for i in listGates:
            if i != "YFP":
                rbs_matches = self.geneticPartsDf.loc[self.geneticPartsDf.gate == i].part.values
                if len(rbs_matches) == 0:
                    continue
                rbs = rbs_matches[0]
                self.gateRBS[i] = rbs

    def _part_sequence(self, part_name):
        rows = self.geneticPartsDf.loc[self.geneticPartsDf.part == part_name]
        if rows.empty:
            raise ValueError(f"Missing genetic part metadata for '{part_name}'")
        return rows.part.values[0], rows.sequence.values[0]

    def _add_component_definition_once(self, doc, component_definition, seen_definitions):
        if component_definition.identity in seen_definitions:
            return
        doc.addComponentDefinition(component_definition)
        seen_definitions.add(component_definition.identity)

    def _add_sequence_once(self, doc, sequence_obj, seen_sequences):
        if sequence_obj.identity in seen_sequences:
            return
        doc.addSequence(sequence_obj)
        seen_sequences.add(sequence_obj.identity)

    def _unique_display_id(self, counters, base_name):
        counters[base_name] = counters.get(base_name, 0) + 1
        return f"{base_name}_{counters[base_name]}"

    def ListOfLines(self, circuits):
        #This function filters out the unwanted characters from every line of each circuit
        chac = '->|^'
        Component_strings = []
        for i in circuits:
            line = []
            for j in i:
                str = ''
                for k in j:
                    if k not in chac:
                        str += k
                line.append(str)
            Component_strings.append(line)

        return Component_strings

    def _get_reporter_token(self, componentDef_string):
        """Return the reporter CDS token from the first circuit line."""
        if not componentDef_string or not componentDef_string[0]:
            raise ValueError("No circuit components available for SBOL generation")

        cds_tokens = [
            token for token in componentDef_string[0]
            if token and token[0] == '(' and token[-1] == ')'
        ]
        if not cds_tokens:
            raise ValueError("No reporter CDS found in generated circuit")
        return cds_tokens[-1]

    def CreateFile(self, input_list, circuits, total_gates, total_time, option, num):
        for i in range(circuits): #iter for each circuit
            file_num = SortNum(i, option) + 1
            if Total_Gates(i) <= total_gates and Total_time(i) <= total_time and file_num <= num:   #If Total Delay and number of gates are less than the input
                setHomespace('http://sbols.org/Output_Circuit'+str(i)) #sets the default URI prefix for every object
                #To avoid collision in objects, as we don't want to use the same Id in different type of objects
                Config.setOption('sbol_typed_uris', False)
                Config.setOption('validate', False)
                Config.setOption('validate_online', False)
                version = '1.0.0' #There will only be one version of every object
                doc=Document()
                seen_definitions = set()
                seen_sequences = set()
                circuit_object_counts = {}
                component_defs = [] #A list to contain objects themselves
                componentDef_string = [] #A list to contain name of the objects
                count=1 #A variable to assign number to terminators

                #Create ModuleDefinition of the device, which will contain the FunctionalComponent of the device connected to its ComponentDefinition
                Circuit = ModuleDefinition('Output_Circuit_' + str(i+1))
                Circuit.name = 'Output Circuit Module'
                doc.addModuleDefinition(Circuit)

                #Create ComponentDefinition for the whole Device which will contain the Components of each part and the SequenceConstraints
                Device = ComponentDefinition('Output_Device_' + str(i+1))
                Device.name = 'Output_Device ' + str(i+1) + ' Component'
                doc.addComponentDefinition(Device)


                circuit_fc_id = self._unique_display_id(circuit_object_counts, 'Device')
                Circuit_fc = Circuit.functionalComponents.create(circuit_fc_id)
                Circuit_fc.name = 'Device'
                #This Functional Component needs a unique ID of the part it belongs to, in this case it belongs to the Device itself
                Circuit_fc.definition = Device.identity
                Circuit_fc.access = SBOL_ACCESS_PUBLIC
                Circuit_fc.direction = SBOL_DIRECTION_NONE

                ### Terminator ###
                terminator = self.geneticPartsDf.loc[self.geneticPartsDf.type == "Terminator"]
                terminatorName = terminator.part.values[0]
                terminatorSeq = terminator.sequence.values[0]
                terminatorSeqObj = Sequence(terminatorName+"_sequence", terminatorSeq)
                self._add_sequence_once(doc, terminatorSeqObj, seen_sequences)

                sequences = [terminatorSeqObj] #these will be added later to the doc
                finalSequenceList = []
                Terminator = ComponentDefinition(terminatorName, BIOPAX_DNA)
                Terminator.roles = SO_TERMINATOR
                Terminator.sequence = terminatorSeqObj
                self._add_component_definition_once(doc, Terminator, seen_definitions)

                for j in range(len(input_list[i])): #iter for each line of the circuit
                    splitted_components = input_list[i][j].split()      #each part in a line
                    name_line = []      #List to contain names of each part
                    def_line = []       #List to contain Component Definitions of each part
                    for k in range(len(splitted_components)):       #Loop to get the individual names of promotors and coding sequences in the list
                        if splitted_components[k][0] == '(':        #if the part is a coding sequence
                            name = splitted_components[k][1:-1]
                            Comp = ComponentDefinition(name, BIOPAX_DNA)
                            Comp.roles = SO_CDS
                            seqName, seqValue = self._part_sequence(name)
                            seqObj = Sequence(seqName+"_sequence", seqValue)
                            sequences.append(seqObj)
                            self._add_sequence_once(doc, seqObj, seen_sequences)
                            Comp.sequence = seqObj

                            if name != "YFP" and name in self.gateRBS:
                                rbs = self.gateRBS[name]
                                seqName, seqValue = self._part_sequence(rbs)
                                seqObj = Sequence(seqName+"_sequence", seqValue)
                                sequences.append(seqObj)
                                self._add_sequence_once(doc, seqObj, seen_sequences)
                                RBS = ComponentDefinition(rbs, BIOPAX_DNA)
                                RBS.roles = SO_RBS
                                RBS.sequence = seqObj

                                self._add_component_definition_once(doc, RBS, seen_definitions)

                                def_line.append(RBS)
                                name_line.append(rbs)

                            def_line.append(Comp)
                            name_line.append(splitted_components[k])

                            Terminator = ComponentDefinition(terminatorName+"__"+str(count), BIOPAX_DNA)
                            Terminator.roles = SO_TERMINATOR
                            Terminator.sequence = terminatorSeqObj
                            def_line.append(Terminator)
                            name_line.append(terminatorName+"__"+str(count))

                            #Terminator = ComponentDefinition('Terminator' + str(count), BIOPAX_DNA)
                            #Terminator.roles = SO_TERMINATOR
                            #doc.addComponentDefinition(Terminator)
                            #def_line.append(Terminator)
                            #name_line.append('Terminator' + str(count))
                            count+=1
                        else:
                            Comp = ComponentDefinition(splitted_components[k], BIOPAX_DNA)
                            Comp.roles = SO_PROMOTER
                            seqName, seqValue = self._part_sequence(splitted_components[k])
                            seqObj = Sequence(seqName+"_sequence", seqValue)
                            sequences.append(seqObj)
                            self._add_sequence_once(doc, seqObj, seen_sequences)
                            Comp.sequence = seqObj

                            def_line.append(Comp)
                            name_line.append(splitted_components[k])

                        self._add_component_definition_once(doc, Comp, seen_definitions)

                    component_defs.append(def_line)
                    componentDef_string.append(name_line)

                #if circuit has 2 lines, add the 2nd line to the start of the first to match sbol visaul
                if not component_defs or not componentDef_string:
                    continue
                if len(component_defs) > 1:
                    finalComp = component_defs[1][:]
                    finalCompString = componentDef_string[1][:]
                    finalComp.extend(component_defs[0][:])
                    finalCompString.extend(componentDef_string[0][:])
                else:
                    finalComp = component_defs[0][:]
                    finalCompString = componentDef_string[0][:]
                #print(finalComp)
                #print(componentDef_string)
                #print(finalCompString)
                # Primary structure is assembled manually below by creating Components and
                # SequenceConstraints. Calling assemblePrimaryStructure here re-adds repeated
                # ComponentDefinitions like PAmtR to the Document and breaks on duplicate URIs.
                #print("DNA : ", Device.compile())
                #For the Flourescent Protein, which is the last element of the first line of the circuit
                reporter_token = self._get_reporter_token(componentDef_string)
                reporter_name = reporter_token[1:-1]
                FP_protein = ComponentDefinition(reporter_name+'_Protein', BIOPAX_PROTEIN)
                self._add_component_definition_once(doc, FP_protein, seen_definitions)

                FP_protein_c = Device.components.create(reporter_name+'_Protein')
                FP_protein_c.definition = FP_protein.identity
                FP_protein_c.access = SBOL_ACCESS_PUBLIC

                Components = []     #List to store all the Components class of each part
                component_instance_counts = {}
                for j in range(len(componentDef_string)):       #This loop creates those Components
                    Components_line = []
                    for k in range(len(componentDef_string[j])):
                        base_name = componentDef_string[j][k]
                        if componentDef_string[j][k][0] == '(':
                            base_name = componentDef_string[j][k][1:-1]

                        component_instance_counts[base_name] = component_instance_counts.get(base_name, 0) + 1
                        name = f"{base_name}_component_{component_instance_counts[base_name]}"

                        name_c = Device.components.create(name)
                        name_c.definition = component_defs[j][k].identity
                        name_c.access = SBOL_ACCESS_PUBLIC
                        Components_line.append(name_c)

                    Components.append(Components_line)

                s_contraint_list = []
                for j in range(len(componentDef_string)):       #This loop is to create the SequenceConstraints class to defines the Orientation of the device
                    for k in range(len(componentDef_string[j])-1):

                        if componentDef_string[j][k+1][0] == '(':
                            name = componentDef_string[j][k] + '_precedes_' + componentDef_string[j][k+1][1:-1]
                            #S_constraint = Device.sequenceConstraints.create(componentDef_string[j][k] + '_precedes_' + componentDef_string[j][k+1][1:-1])

                        elif componentDef_string[j][k][0] == '(':
                            name = componentDef_string[j][k][1:-1] + '_precedes_' + componentDef_string[j][k+1]
                            #S_constraint = Device.sequenceConstraints.create(componentDef_string[j][k][1:-1] + '_precedes_' + componentDef_string[j][k+1])

                        else:
                            name = componentDef_string[j][k] + '_precedes_' + componentDef_string[j][k+1]
                            #S_constraint = Device.sequenceConstraints.create(componentDef_string[j][k] + '_precedes_' + componentDef_string[j][k+1])

                        if name not in s_contraint_list:
                            s_contraint_list.append(name)
                            S_constraint = Device.sequenceConstraints.create(name)
                            S_constraint.subject = Components[j][k].identity        #Subject is the part that comes first
                            S_constraint.object = Components[j][k+1].identity       #Object is the part that comes later
                            S_constraint.restriction = SBOL_RESTRICTION_PRECEDES    #This describes the order we have defined for this Constraint

                        if j == 0 and componentDef_string[j][k][0] == '(':      #for the coding sequences in the first line of the circuit
                            #For the Module Definition, we only need the coding sequence and the output promotor
                            cds_fc_id = self._unique_display_id(circuit_object_counts, componentDef_string[j][k][1:-1])
                            cds_fc = Circuit.functionalComponents.create(cds_fc_id)
                            cds_fc.definition = component_defs[j][k].identity       #Connected to its ComponentDefinition class
                            cds_fc.access = SBOL_ACCESS_PUBLIC
                            cds_fc.direction = SBOL_DIRECTION_NONE

                            if componentDef_string[j][k] != reporter_token:     #If the component is not the flourescent protein
                                #Create Functional Component of the output promotor
                                if k + 2 >= len(componentDef_string[j]):
                                    continue
                                p_fc_id = self._unique_display_id(circuit_object_counts, componentDef_string[j][k+2])
                                P_fc = Circuit.functionalComponents.create(p_fc_id)
                                P_fc.definition = component_defs[j][k+2].identity
                                P_fc.access = SBOL_ACCESS_PUBLIC
                                P_fc.direction = SBOL_DIRECTION_NONE

                                #Define the Interaction between those two Functional Components
                                repression_id = self._unique_display_id(circuit_object_counts, componentDef_string[j][k][1:-1] + '_represses_' + componentDef_string[j][k+2])
                                Repression= Circuit.interactions.create(repression_id)
                                Repression.types = SBO_INHIBITION

                                cds_participation_id = self._unique_display_id(circuit_object_counts, componentDef_string[j][k][1:-1] + '_participant')
                                cds_participation = Repression.participations.create(cds_participation_id)
                                cds_participation.roles = SBO_INHIBITOR
                                cds_participation.participant = cds_fc.identity

                                p_participation_id = self._unique_display_id(circuit_object_counts, componentDef_string[j][k+2] + '_participant')
                                P_participation = Repression.participations.create(p_participation_id)
                                P_participation.roles = SBO_INHIBITED
                                P_participation.participant = P_fc.identity

                                #Map the participants from ModuleDefinition to their Component
                                cds_map_id = self._unique_display_id(circuit_object_counts, componentDef_string[j][k][1:-1] + '_map')
                                cds_map = Circuit_fc.mapsTos.create(cds_map_id)
                                cds_map.refinement = SBOL_REFINEMENT_USE_REMOTE
                                cds_map.local = cds_fc.identity
                                cds_map.remote = Components[j][k].identity

                                p_map_id = self._unique_display_id(circuit_object_counts, componentDef_string[j][k+2] + '_map')
                                P_map = Circuit_fc.mapsTos.create(p_map_id)
                                P_map.refinement = SBOL_REFINEMENT_USE_REMOTE
                                P_map.local = P_fc.identity
                                P_map.remote = Components[j][k+2].identity

                            else:       #If its Flourescent Protein
                                fp_fc_id = self._unique_display_id(circuit_object_counts, reporter_name+'_Protein')
                                FP_fc = Circuit.functionalComponents.create(fp_fc_id)
                                FP_fc.definition = FP_protein.identity
                                FP_fc.access = SBOL_ACCESS_PUBLIC
                                FP_fc.direction = SBOL_DIRECTION_NONE

                                production_id = self._unique_display_id(circuit_object_counts, reporter_name+'_produces_'+reporter_name+'_Protein')
                                Production= Circuit.interactions.create(production_id)
                                Production.types = SBO_GENETIC_PRODUCTION

                                cds_participation_id = self._unique_display_id(circuit_object_counts, componentDef_string[j][k][1:-1] + '_participant')
                                cds_participation = Production.participations.create(cds_participation_id)
                                cds_participation.roles = SBO + '0000645'       #The role for the coding sequence of the flourescent protein is not defined
                                cds_participation.participant = cds_fc.identity

                                fp_participation_id = self._unique_display_id(circuit_object_counts, reporter_name+'_Protein_participant')
                                FP_participation = Production.participations.create(fp_participation_id)
                                FP_participation.roles = SBO_PRODUCT
                                FP_participation.participant = FP_fc.identity

                                cds_map_id = self._unique_display_id(circuit_object_counts, componentDef_string[j][k][1:-1] + '_map')
                                cds_map = Circuit_fc.mapsTos.create(cds_map_id)
                                cds_map.refinement = SBOL_REFINEMENT_USE_REMOTE
                                cds_map.local = cds_fc.identity
                                cds_map.remote = Components[j][k].identity

                                fp_map_id = self._unique_display_id(circuit_object_counts, reporter_name+'_Protein_map')
                                FP_map = Circuit_fc.mapsTos.create(fp_map_id)
                                FP_map.refinement = SBOL_REFINEMENT_USE_REMOTE
                                FP_map.local = FP_fc.identity
                                FP_map.remote = FP_protein_c.identity

                    if j != 0 and componentDef_string[j] and Components[j]:        #For the remaining lines of the circuit
                        if j == len(componentDef_string)-1 and componentDef_string[0] and Components[0]:     #To avoid intersection of Repression Lines
                            #The sequnece was already made for the lines but we have to connect this part to the circuit as well, so it gets connected to the first part in first line of the circuit
                            S_constraint = Device.sequenceConstraints.create(componentDef_string[j][-1] + '_precedes_' + componentDef_string[0][0])
                            S_constraint.subject = Components[j][-1].identity
                            S_constraint.object = Components[0][0].identity
                            S_constraint.restriction = SBOL_RESTRICTION_PRECEDES
                        elif j + 1 < len(componentDef_string) and componentDef_string[j+1] and Components[j+1]:
                            S_constraint = Device.sequenceConstraints.create(componentDef_string[j][-1] + '_precedes_' + componentDef_string[j+1][0])
                            S_constraint.subject = Components[j][-1].identity
                            S_constraint.object = Components[j+1][0].identity
                            S_constraint.restriction = SBOL_RESTRICTION_PRECEDES

                        for k_secondary, component_name in enumerate(componentDef_string[j]):
                            if not component_name or component_name[0] != '(':
                                continue

                            cds_name = component_name[1:-1]
                            cds_fc_id = self._unique_display_id(circuit_object_counts, cds_name)
                            cds_fc = Circuit.functionalComponents.create(cds_fc_id)
                            cds_fc.definition = component_defs[j][k_secondary].identity
                            cds_fc.access = SBOL_ACCESS_PUBLIC
                            cds_fc.direction = SBOL_DIRECTION_NONE

                            promoter_name = 'P' + cds_name
                            target_line_index = None
                            index_of_myP = None
                            for candidate_line_index, candidate_line in enumerate(componentDef_string[:min(2, len(componentDef_string))]):
                                if promoter_name in candidate_line:
                                    target_line_index = candidate_line_index
                                    index_of_myP = candidate_line.index(promoter_name)
                                    break

                            if target_line_index is None or index_of_myP is None:
                                continue

                            p_fc_id = self._unique_display_id(circuit_object_counts, componentDef_string[target_line_index][index_of_myP])
                            P_fc = Circuit.functionalComponents.create(p_fc_id)
                            P_fc.definition = component_defs[target_line_index][index_of_myP].identity
                            P_fc.access = SBOL_ACCESS_PUBLIC
                            P_fc.direction = SBOL_DIRECTION_NONE

                            repression_id = self._unique_display_id(circuit_object_counts, cds_name + '_represses_' + componentDef_string[target_line_index][index_of_myP])
                            Repression= Circuit.interactions.create(repression_id)
                            Repression.types = SBO_INHIBITION

                            cds_participation_id = self._unique_display_id(circuit_object_counts, cds_name + '_participant')
                            cds_participation = Repression.participations.create(cds_participation_id)
                            cds_participation.roles = SBO_INHIBITOR
                            cds_participation.participant = cds_fc.identity

                            p_participation_id = self._unique_display_id(circuit_object_counts, componentDef_string[target_line_index][index_of_myP] + '_participant')
                            P_participation = Repression.participations.create(p_participation_id)
                            P_participation.roles = SBO_INHIBITED
                            P_participation.participant = P_fc.identity

                            cds_map_id = self._unique_display_id(circuit_object_counts, cds_name + '_map')
                            cds_map = Circuit_fc.mapsTos.create(cds_map_id)
                            cds_map.refinement = SBOL_REFINEMENT_USE_REMOTE
                            cds_map.local = cds_fc.identity
                            cds_map.remote = Components[j][k_secondary].identity

                            p_map_id = self._unique_display_id(circuit_object_counts, componentDef_string[target_line_index][index_of_myP] + '_map')
                            P_map = Circuit_fc.mapsTos.create(p_map_id)
                            P_map.refinement = SBOL_REFINEMENT_USE_REMOTE
                            P_map.local = P_fc.identity
                            P_map.remote = Components[target_line_index][index_of_myP].identity
                #print("here")
                result = doc.write(str(USER_FILES_DIR / ("SBOL File " + str(file_num) + ".xml")))        #To save the SBOL File
                #print("here ", result)

if __name__ == '__main__':
    #inputExp = "IPTG'.aTc'.Arabinose'+IPTG'.aTc.Arabinose'+IPTG.aTc'.Arabinose'"
    f = SBOL_File(1000, 1000)
