"""
  based on ASE script for Mopac


"""
import os
import string
import numpy as np
from ase.io import write
from ase.units import kcal, mol
from ase.units import Hartree, Bohr
from ase.calculators.general import Calculator
import copy

key_parameters={'seed':1351351,'multibasis':'Se lanl2dz_ecp\nCl lanl2dz_ecp\nCd lanl2dz_ecp\nZn lanl2dz_ecp\nMg lanl2dz_ecp','maxit':200,'gpumem':512,'gpus':None,'basis':None,'coordinates':None,'charge':None,'method':None,'dftd':None,'run':None,'pointcharges':None ,'threall':1.0e-12,'scf':'diis','watcheindiis' :'no'}

class TeraChem(Calculator):
    name = 'TeraChem'
    def __init__(self, label='ase',terachem_file=False,gpus='1    1',basis='6-31g',coordinates='tmp_ase.pdb',charge='0',method='rhf',dftd='yes',run='gradient',atoms=None, **kwargs):
	self.terachem_file=terachem_file
        coordinates=os.path.dirname(label)+"/"+ coordinates
	self.coordinates=coordinates
        self.key_parameters = copy.deepcopy(key_parameters)
	self.key_parameters['gpus']=gpus
	self.key_parameters['basis']=basis
	self.key_parameters['coordinates']=coordinates
	self.key_parameters['charge']=charge
	self.key_parameters['method']=method
	self.key_parameters['dftd']=dftd
	self.key_parameters['run']=run
        # save label
        self.label = label
        #set atoms
        self.atoms = atoms
        # initialize the results
        self.version = None
        self.energy_zero = None
        self.energy_free = None
        self.forces = None
        self.stress = None


    def write_input(self, fname, atoms):
	key_parameters = self.key_parameters
	if self.terachem_file==True:
        	pass
	#print "use the existing terachem input file"
	else:
	    	if self.atoms!=None:
			atoms = copy.deepcopy(self.atoms)
			atoms.set_pbc(pbc=(0,0,0))
			write(self.coordinates,atoms)
	    	finput = open(fname,"w")
                working_dir = os.path.dirname(self.coordinates)
                key_parameters["scrdir"] = working_dir + "/scr"
                if os.path.exists(key_parameters["scrdir"]+"/c0"):
                  key_parameters["guess"] =  key_parameters["scrdir"]+"/c0"
                else:
                  key_parameters["guess"] = None
                for key, value in key_parameters.iteritems():
			if(value!=None):
				if  not isinstance(value, str):
					value = str(value)
                                if key is  'multibasis':
                                  finput.write('$multibasis \n')
                                  for item in value.split(','):
                                    line = ' '.join([item,'\n'])
                                    finput.write(line)
                                  finput.write('$end \n')
                                else:
				  line=' '.join([key,value,'\n'])
				  finput.write(line)
		finput.write('end')
		finput.close()
    def get_command(self):
        """Return command string if program installed, otherwise None.  """
        command = None
        if ('TeraChem_COMMAND' in os.environ):
            command = os.environ['TeraChem_COMMAND']
        return command

    def run_qr(atoms,
               charge=None,
               pointcharges=None,
               coordinates=None,
               define_str=None):
        pass

    def run(self):
	import subprocess
        """
        Writes input in label.mop
        Runs TeraChem
        Reads Version, Energy and Forces
        """
        # set the input file name
        finput = self.label + '.sp'
        foutput = self.label + '.out'
        self.write_input(finput, self.atoms)

        working_dir = os.path.dirname(finput)
        key_parameters["scrdir"] = working_dir + "/scr"
        command = self.get_command()
        if command is None:
            raise RuntimeError('TeraChem command not specified')
	#print ('%s %s' % (command, finput) + '  >     '+ foutput + '  2>&1')
	exitcode = os.system('%s %s' % (command, finput) + '  >     '+ foutput + '  2>&1')
        if exitcode != 0:

            raise RuntimeError('TeraChem exited with error code')


        energy = self.read_energy(foutput)
        self.energy_zero = energy
        self.energy_free = energy

        self.forces = self.read_forces(foutput)
    def read_energy(self, fname):
        """
        Reads the ENERGY from the output file (FINAL ENERGY in a.u.)
        Raises RuntimeError if no energy was found
        """
        outfile = open(fname)
        lines = outfile.readlines()
        outfile.close()

        energy = None
        for line in lines:
            if line.find('FINAL ENERGY:') != -1:
                words = line.split()
                energy = float(words[2])
        if energy is None:
            raise RuntimeError('TeraChem: could not find total energy')
        energy *= (Hartree)/(kcal / mol)
        return energy

    def read_forces(self, fname):
        """
        Reads the FORCES from the output file
        search string: (Gradient units are Hartree/Bohr)
        """
        outfile = open(fname)
        lines = outfile.readlines()
        outfile.close()

        nats = len(self.atoms)
        forces = np.zeros((nats, 3), float)

        infinite_force="*****"
        for i, line in enumerate(lines):
            if line.find('Gradient units') != -1:
                for j in range(nats ):
                    atom_force = []
                    gline = lines[i + j + 3]
                    pre_force=gline.split()
                    for each_force in pre_force:
                       if infinite_force in each_force:
                             each_force = 999999999.9999
                       atom_force.append(each_force)
                    forces[j]=atom_force
                break
        forces *= -(Hartree/Bohr)/(kcal / mol)
        return forces

    def atoms_are_equal(self, atoms_new):
        ''' (adopted from jacapo.py)
        comparison of atoms to self.atoms using tolerances to account
        for float/double differences and float math.
        '''

        TOL = 1.0e-6  # angstroms

        # check for change in cell parameters
        test = len(atoms_new) == len(self.atoms)
        if test is not True:
            return False

        # check for change in cell parameters
        test = (abs(self.atoms.get_cell() - atoms_new.get_cell()) <= TOL).all()
        if test is not True:
            return False

        old = self.atoms.arrays
        new = atoms_new.arrays

        # check for change in atom position
        test = (abs(new['positions'] - old['positions']) <= TOL).all()
        if test is not True:
            return False

        # passed all tests
        return True

    def update(self, atoms_new):
        if not self.atoms_are_equal(atoms_new):
            self.atoms = atoms_new.copy()
            self.run()
    def set_atoms(self, atoms):
	self.atoms=atoms

    def set(self, **kwargs):
	for key, value in kwargs.items():
 		self.key_parameters[str(key)]=value