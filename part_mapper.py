"""
part_mapper.py - Maps GeneTech parts to iGEM part numbers
"""

class PartMapper:
    """
    This class knows which iGEM part corresponds to each GeneTech part
    """
    
    def __init__(self):
        # This dictionary maps your part names to iGEM part numbers
        self.mapping = {
            # Input Promoters (from your GatesLib.txt)
            'PTac': 'BBa_K864500',      # Tac promoter
            'PTet': 'BBa_R0040',         # TetR repressible promoter
            'PBad': 'BBa_I0500',         # Arabinose promoter
            
            # Output Promoters
            'PAmtR': 'BBa_K1372007',     # AmtR repressible promoter
            'PAmeR': 'BBa_K1372008',      # AmeR repressible promoter
            'PHlYllR': 'BBa_K1372009',    # HlyIIR repressible promoter
            'PSrpR': 'BBa_K1372010',      # SrpR repressible promoter
            'PPhlF': 'BBa_K1372011',      # PhlF repressible promoter
            'PBM3R1': 'BBa_K1372012',     # BM3R1 repressible promoter
            'PBetl': 'BBa_K1372013',      # BetI repressible promoter
            
            # Repressor Proteins (CDS)
            'AmtR': 'BBa_K1372001',      # AmtR repressor
            'AmeR': 'BBa_K1372002',      # AmeR repressor
            'HlYllR': 'BBa_K1372003',    # HlyIIR repressor
            'SrpR': 'BBa_K1372004',      # SrpR repressor
            'PhlF': 'BBa_K1372005',      # PhlF repressor
            'BM3R1': 'BBa_K1372006',     # BM3R1 repressor
            'Betl': 'BBa_K1372014',      # BetI repressor
            
            # Terminator
            'ECK120033737': 'BBa_B0015', # Double terminator
            
            # Reporter
            'YFP': 'BBa_E0030',          # YFP reporter
            
            # RBS (Ribosome Binding Sites)
            'A1': 'BBa_B0034',           # RBS for AmtR
            'F1': 'BBa_B0034',           # RBS for AmeR
            'H1': 'BBa_B0034',           # RBS for HlyIIR
            'S1': 'BBa_B0034',           # RBS for SrpR
            'P1': 'BBa_B0034',           # RBS for PhlF
            'B1': 'BBa_B0034',           # RBS for BM3R1
            'E1': 'BBa_B0034',           # RBS for BetI
        }
        
        print(f"✅ PartMapper loaded with {len(self.mapping)} parts")
    
    def get_igem_id(self, genetech_part):
        """
        Get iGEM ID for a GeneTech part
        Example: get_igem_id('PTac') returns 'BBa_K864500'
        """
        if genetech_part in self.mapping:
            return self.mapping[genetech_part]
        return None
    
    def get_all_parts(self):
        """Return all GeneTech part names"""
        return list(self.mapping.keys())
    
    def reverse_lookup(self, igem_id):
        """
        Find which GeneTech part corresponds to an iGEM ID
        """
        for genetech_part, iid in self.mapping.items():
            if iid == igem_id:
                return genetech_part
        return None

# Test the mapper
if __name__ == "__main__":
    mapper = PartMapper()
    
    print("\n" + "="*50)
    print("TESTING PART MAPPER")
    print("="*50)
    
    # Test a few parts
    test_parts = ['PTac', 'AmtR', 'YFP', 'PAmtR', 'Unknown']
    
    print("\n📋 Testing Part Mapper:")
    print("-"*40)
    for part in test_parts:
        igem_id = mapper.get_igem_id(part)
        if igem_id:
            print(f"   ✅ {part} → {igem_id}")
        else:
            print(f"   ❌ {part} → No mapping found")