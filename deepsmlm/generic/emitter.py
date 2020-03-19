import warnings

import numpy as np
import torch

from .utils import test_utils as tutil
from .utils import generic as gutil


class EmitterSet:
    """
    Class, storing a set of emitters and its attributes. Probably the most commonly used class of this framework.

    Attributes:
            xyz: Coordinates of size N x [2,3].
            phot: Photon count of size N
            frame_ix: size N. Index on which the emitter appears.
            id: size N. Identity the emitter.
            prob: size N. Probability estimate of the emitter.
            bg: size N. Background estimate of emitter.
            xyz_cr: size N x 3. Cramer-Rao estimate of the emitters position.
            phot_cr: size N. Cramer-Rao estimate of the emitters photon count.
            bg_cr: size N. Cramer-Rao estimate of the emitters background value.
            sanity_check: performs a sanity check if true.
            xy_unit: Unit of the x and y coordinate.
            px_size: Pixel size for unit conversion. If not specified, derived attributes (xyz_px and xyz_nm)
                can not be accessed
    """
    eq_precision = 1E-8
    xy_units = ('px', 'nm')

    def __init__(self, xyz: torch.Tensor, phot: torch.Tensor, frame_ix: torch.Tensor,
                 id: torch.Tensor = None, prob: torch.Tensor = None, bg: torch.Tensor = None,
                 xyz_cr: torch.Tensor = None, phot_cr: torch.Tensor = None, bg_cr: torch.Tensor = None,
                 sanity_check: bool = True, xy_unit=None, px_size=None):
        """
        Initialises EmitterSet of size N.

        Args:
            xyz: Coordinates of size N x [2,3]. Must be tensor float type
            phot: Photon count of size N (will be converted to float)
            frame_ix: size N. Index on which the emitter appears. Must be tensor integer type
            id: size N. Identity the emitter. Must be tensor integer type and the same type as frame_ix
            prob: size N. Probability estimate of the emitter.
            bg: size N. Background estimate of emitter.
            xyz_cr: size N x 3. Cramer-Rao estimate of the emitters position.
            phot_cr: size N. Cramer-Rao estimate of the emitters photon count.
            bg_cr: size N. Cramer-Rao estimate of the emitters background value.
            sanity_check: performs a sanity check if true.
            xy_unit: Unit of the x and y coordinate.
            px_size: Pixel size for unit conversion. If not specified, derived attributes (xyz_px and xyz_nm)
                can not be accessed
        """

        self.xyz = None
        self.phot = None
        self.frame_ix = None
        self.id = None
        self.prob = None
        self.bg = None

        # Cramer-Rao values
        self.xyz_cr = None
        self.phot_cr = None
        self.bg_cr = None

        self._set_typed(xyz=xyz, phot=phot, frame_ix=frame_ix, id=id, prob=prob, bg=bg,
                        xyz_cr=xyz_cr, phot_cr=phot_cr, bg_cr=bg_cr)

        self._sorted = False
        # get at least one_dim tensors
        tutil.at_least_one_dim(self.xyz,
                               self.phot,
                               self.frame_ix,
                               self.id,
                               self.prob,
                               self.bg,
                               self.xyz_cr,
                               self.phot_cr,
                               self.bg_cr)

        self.xy_unit = xy_unit
        self.px_size = px_size
        if self.px_size is not None:
            if not isinstance(self.px_size, torch.Tensor):
                self.px_size = torch.Tensor(self.px_size)

        if sanity_check:
            self._sanity_check()

    def _set_typed(self, xyz, phot, frame_ix, id, prob, bg, xyz_cr, phot_cr, bg_cr):
        """
        Sets the attributes in the correct type and with default argument if None
        """

        if xyz.dtype not in (torch.float, torch.double, torch.half):
            raise ValueError("XYZ coordinates must be float type.")
        else:
            f_type = xyz.dtype

        if frame_ix.dtype not in (torch.int16, torch.int32, torch.int64):
            raise ValueError(f"Frame index must be integer type and not {frame_ix.dtype}")

        if id is not None and (id.dtype not in (torch.int16, torch.int32, torch.int64) or id.dtype != frame_ix.dtype):
            raise ValueError(f"ID must be None or integer type and the same as frame_ix dtype and not {id.dtype}")
        else:
            i_type = frame_ix.dtype

        xyz = xyz if xyz.shape[1] == 3 else torch.cat((xyz, torch.zeros_like(xyz[:, [0]])), 1)

        num_input = int(xyz.shape[0]) if xyz.shape[0] != 0 else 0

        """Set values"""
        if num_input != 0:
            self.xyz = xyz
            self.phot = phot.type(f_type)
            self.frame_ix = frame_ix

            # Optionals
            self.id = id if id is not None else -torch.ones_like(frame_ix)
            self.prob = prob if prob is not None else torch.ones_like(frame_ix).type(f_type)
            self.bg = bg if bg is not None else float('nan') * torch.ones_like(frame_ix).type(f_type)
            self.xyz_cr = xyz_cr if xyz_cr is not None else float('nan') * torch.ones_like(self.xyz)
            self.phot_cr = phot_cr if phot_cr is not None else float('nan') * torch.ones_like(self.phot)
            self.bg_cr = bg_cr if bg_cr is not None else float('nan') * torch.ones_like(self.bg)

        else:
            self.xyz = torch.zeros((0, 3)).type(f_type)
            self.phot = torch.zeros((0,)).type(f_type)
            self.frame_ix = torch.zeros((0,)).type(i_type)

            # Optionals
            self.id = -torch.ones((0,)).type(i_type)
            self.prob = torch.ones((0,)).type(f_type)
            self.bg = float('nan') * torch.ones_like(self.prob)
            self.xyz_cr = float('nan') * torch.ones((0, 3)).type(f_type)
            self.phot_cr = float('nan') * torch.ones_like(self.prob)
            self.bg_cr = float('nan') * torch.ones_like(self.prob)

    def to_dict(self):
        """
        Returns dictionary representation of this EmitterSet so that the keys and variables correspond to what an
        EmitterSet would be initialised.

        Returns:
            (dict)
        """
        em_dict = {
            'xyz': self.xyz,
            'phot': self.phot,
            'frame_ix': self.frame_ix,
            'id': self.id,
            'prob': self.prob,
            'bg': self.bg,
            'xyz_cr': self.xyz_cr,
            'phot_cr': self.phot_cr,
            'bg_cr': self.bg_cr,
            'xy_unit': self.xy_unit,
            'px_size': self.px_size
        }

        return em_dict

    @property
    def num_emitter(self):
        raise DeprecationWarning

    @property
    def xyz_px(self):
        """
        Returns xyz in pixel coordinates and performs respective transformations if needed.
        """
        if self.xy_unit is None:
            warnings.warn("If unit is unspecified, can not convert to px coordinates.")
            return
        elif self.xy_unit == 'nm':
            if self.px_size is None:
                raise ValueError("Cannot convert between px and nm without px-size specified.")
            return self._convert_coordinates(factor=1 / self.px_size)
        elif self.xy_unit == 'px':
            return self.xyz

    @xyz_px.setter
    def xyz_px(self, xyz):
        self.xyz = xyz
        self.xy_unit = 'px'

    @property
    def xyz_nm(self):
        """
        Returns xyz in nanometres and performs respective transformations if needed.
        """
        if self.xy_unit is None:
            warnings.warn("If unit is unspecified, can not convert to px coordinates.")
            return
        elif self.xy_unit == 'px':
            if self.px_size is None:
                raise ValueError("Cannot convert between px and nm without px-size specified.")
            return self._convert_coordinates(factor=self.px_size)
        elif self.xy_unit == 'nm':
            return self.xyz

    @xyz_nm.setter
    def xyz_nm(self, xyz):  # xyz in nanometres
        self.xyz = xyz
        self.xy_unit = 'nm'

    @property
    def xyz_scr(self):  # sqrt cramer-rao of xyz in px
        return self.xyz_cr.sqrt()

    @property
    def xyz_nm_scr(self):  # sqrt cramer-rao of xyz in nm
        if self.px_size is None:
            raise ValueError("Cannot convert between px and nm without px-size specified.")
        return self._convert_coordinates(factor=self.px_size, xyz=self.xyz_scr)

    @property
    def phot_scr(self):  # sqrt cramer-rao of photon count
        return self.phot_cr.sqrt()

    @property
    def bg_scr(self):  # sqrt cramer-rao of bg count
        return self.bg_cr.sqrt()

    def _inplace_replace(self, em):
        """
        Inplace replacement of this self instance. Does not work for inherited methods ...
        Args:
            em: (EmitterSet) that should replace self

        Returns:
            (None)
        """
        self.__init__(xyz=em.xyz,
                      phot=em.phot,
                      frame_ix=em.frame_ix,
                      id=em.id,
                      prob=em.prob,
                      bg=em.bg,
                      xyz_cr=em.xyz_cr,
                      phot_cr=em.phot_cr,
                      bg_cr=em.bg_cr,
                      sanity_check=True,
                      xy_unit=em.xy_unit,
                      px_size=em.px_size)

    def _sanity_check(self, check_uniqueness=False):
        """
        Performs several integrity tests on the EmitterSet.

        Args:
            check_uniqueness: (bool) check the uniqueness of the ID

        Returns:
            (bool) sane or not sane
        """
        if not tutil.same_shape_tensor(0, self.xyz, self.phot, self.frame_ix, self.id, self.bg,
                                       self.xyz_cr, self.phot_cr, self.bg_cr):
            raise ValueError("Coordinates, photons, frame ix, id and prob are not of equal shape in 0th dimension.")

        if not tutil.same_dim_tensor(torch.ones(1), self.phot, self.prob, self.frame_ix, self.id):
            raise ValueError("Expected photons, probability frame index and id to be 1D.")

        # Motivate the user to specify an xyz unit.
        if len(self) > 0:
            if self.xy_unit is None:
                warnings.warn("No xyz unit specified. No guarantees given ...")
            else:
                if self.xy_unit not in self.xy_units:
                    raise ValueError("XY unit not supported.")

        # check uniqueness of identity (ID)
        if check_uniqueness:
            if torch.unique(self.id).numel() != self.id.numel():
                raise ValueError("IDs are not unique.")

        return True

    def __len__(self):
        """
        Implements length of EmitterSet. Length of EmitterSet is number of rows of xyz container.

        Returns:
            (int) length of EmitterSet
        """
        return int(self.xyz.shape[0]) if self.xyz.shape[0] != 0 else 0

    def __str__(self):
        """
        Friendly representation of EmitterSet

        Returns:
            (string) representation of this class
        """
        print_str = f"EmitterSet" \
                    f"\n::num emitters: {len(self)}"

        if len(self) == 0:
            print_str += "\n::frame range: n.a." \
                         "\n::spanned volume: n.a."
        else:
            print_str += f"\n::xy unit: {self.xy_unit}"
            print_str += f"\n::frame range: {self.frame_ix.min().item()} - {self.frame_ix.max().item()}" \
                         f"\n::spanned volume: {self.xyz.min(0)[0].numpy()} - {self.xyz.max(0)[0].numpy()}"
        return print_str

    def __eq__(self, other):
        """
        Implements equalness check. Returns true if all attributes are the same and in the same order. The identy
        does not have to be the same, but the values of the attributes have to.
        Args:
            other: (emitterset)

        Returns:
            (bool) true if as stated above.
        """
        if not tutil.tens_almeq(self.xyz, other.xyz, self.eq_precision):
            return False

        if not tutil.tens_almeq(self.frame_ix, other.frame_ix, self.eq_precision):
            return False

        if not tutil.tens_almeq(self.phot, other.phot, self.eq_precision):
            return False

        if not tutil.tens_almeq(self.prob, other.prob, self.eq_precision):
            return False

        if not self.xy_unit == other.xy_unit:
            return False

        if torch.isnan(self.bg).all():
            if not torch.isnan(other.bg).all():
                return False
        else:
            if not tutil.tens_almeq(self.bg, other.bg, self.eq_precision):
                return False

        if torch.isnan(self.xyz_cr).all():
            if not torch.isnan(other.xyz_cr).all():
                return False
        else:
            if not tutil.tens_almeq(self.bg, other.bg, self.eq_precision):
                return False

        if torch.isnan(self.phot_cr).all():
            if not torch.isnan(other.phot_cr).all():
                return False
        else:
            if not tutil.tens_almeq(self.bg, other.bg, self.eq_precision):
                return False

        if torch.isnan(self.bg_cr).all():
            if not torch.isnan(other.bg_cr).all():
                return False
        else:
            if not tutil.tens_almeq(self.bg, other.bg, self.eq_precision):
                return False

        self.eq_attr(other)
        return True

    def eq_attr(self, other):
        """
        Tests whether the meta data attributes are the same

        Args:
            other: EmitterSet

        Returns:
            (bool)
        """
        if self.px_size is None:
            if other.px_size is None:
                return True
            else:
                return False

        if not (self.px_size == other.px_size).all():
            return False

        if not self.xy_unit == other.xy_unit:
            return False

        return True

    def __iter__(self):
        """
        Implements iterator bookkeeping.

        Returns:
            (self)
        """
        self.n = 0
        return self

    def __next__(self):
        """
        Implements next element in iterator method

        Returns:
            (EmitterSet) next element of iterator

        """
        if self.n <= len(self) - 1:
            self.n += 1
            return self.get_subset(self.n - 1)
        else:
            raise StopIteration

    def __getitem__(self, item):
        """
        Implements array indexing for this class.

        Args:
            item: (int), or indexing

        Returns:
            (EmitterSet)
        """

        if isinstance(item, int) and item >= len(self):
            raise IndexError(f"Index {item} out of bounds of EmitterSet of size {len(self)}")

        return self.get_subset(item)

    def __setitem__(self, key, value):
        raise NotImplementedError

    def clone(self):
        """
        Returns a deep copy of this EmitterSet.

        Returns:
            (EmitterSet)
        """
        return EmitterSet(self.xyz.clone(),
                          self.phot.clone(),
                          self.frame_ix.clone(),
                          self.id.clone(),
                          self.prob.clone(),
                          self.bg.clone(),
                          self.xyz_cr.clone(),
                          self.phot_cr.clone(),
                          self.bg_cr.clone(),
                          sanity_check=False,
                          xy_unit=self.xy_unit,
                          px_size=self.px_size)

    @staticmethod
    def cat(emittersets, remap_frame_ix=None, step_frame_ix: int = None):
        """
        Concatenate multiple emittersets into one emitterset which is returned. Optionally modify the frame indices by
        the arguments.

        Args:
            emittersets: (list of emittersets) emittersets to be concatenated
            remap_frame_ix: (torch.Tensor, optional) index of 0th frame to map the corresponding emitterset to.
            Length must correspond to length of list in first argument.
            step_frame_ix: (int, optional) step size of 0th frame between emittersets.

        Returns:
            (emitterset) concatenated emitterset
        """
        num_emittersets = len(emittersets)

        if remap_frame_ix is not None and step_frame_ix is not None:
            raise ValueError("You cannot specify remap frame ix and step frame ix at the same time.")
        elif remap_frame_ix is not None:
            shift = remap_frame_ix.clone()
        elif step_frame_ix is not None:
            shift = torch.arange(0, num_emittersets) * step_frame_ix
        else:
            shift = torch.zeros(num_emittersets).int()

        total_num_emitter = 0
        for i in range(num_emittersets):
            total_num_emitter += len(emittersets[i])

        xyz = torch.cat([emittersets[i].xyz for i in range(num_emittersets)], 0)
        phot = torch.cat([emittersets[i].phot for i in range(num_emittersets)], 0)
        frame_ix = torch.cat([emittersets[i].frame_ix + shift[i] for i in range(num_emittersets)], 0)
        id = torch.cat([emittersets[i].id for i in range(num_emittersets)], 0)
        prob = torch.cat([emittersets[i].prob for i in range(num_emittersets)], 0)
        bg = torch.cat([emittersets[i].bg for i in range(num_emittersets)], 0)
        xyz_cr = torch.cat([emittersets[i].xyz_cr for i in range(num_emittersets)], 0)
        phot_cr = torch.cat([emittersets[i].phot_cr for i in range(num_emittersets)], 0)
        bg_cr = torch.cat([emittersets[i].bg_cr for i in range(num_emittersets)], 0)

        # px_size and xy unit is taken from the first element that is not None
        xy_unit = None
        px_size = None
        for i in range(num_emittersets):
            if emittersets[i].xy_unit is not None:
                xy_unit = emittersets[i].xy_unit
                break
        for i in range(num_emittersets):
            if emittersets[i].px_size is not None:
                px_size = emittersets[i].px_size
                break

        return EmitterSet(xyz, phot, frame_ix, id, prob, bg, xyz_cr, phot_cr, bg_cr, sanity_check=True,
                          xy_unit=xy_unit, px_size=px_size)

    def sort_by_frame_(self):
        """
        Inplace sort this emitterset by its frame index.

        Returns:

        """
        self.frame_ix, ix = self.frame_ix.sort()
        self.xyz = self.xyz[ix, :]
        self.phot = self.phot[ix]
        self.id = self.id[ix]
        self.prob = self.prob[ix]
        self.bg = self.bg[ix]
        self.xyz_cr = self.xyz_cr[ix]
        self.phot_cr = self.phot_cr[ix]
        self.bg_cr = self.bg_cr[ix]

        self._sorted = True

    def sort_by_frame(self):
        """
        Sort a deepcopy of this emitterset and return it.

        Returns:
            (emitterset) Sorted copy of this emitterset.

        """
        em = self.clone()
        em.sort_by_frame_()

        return em

    def get_subset(self, ix):
        """
        Returns subset of emitterset. Implementation of __getitem__ and __next__ methods.
        Args:
            ix: (int, list) integer index or list of indices

        Returns:
            (EmitterSet)
        """
        if isinstance(ix, int):
            ix = [ix]

        if isinstance(ix, torch.Tensor) and ix.numel() == 1:  # PyTorch single element support
            ix = [int(ix)]

        if isinstance(ix, (np.ndarray, np.generic)) and ix.size == 1:  # numpy support
            ix = [int(ix)]

        return EmitterSet(self.xyz[ix, :], self.phot[ix], self.frame_ix[ix], self.id[ix], self.prob[ix], self.bg[ix],
                          self.xyz_cr[ix], self.phot_cr[ix], self.bg_cr[ix], sanity_check=False,
                          xy_unit=self.xy_unit, px_size=self.px_size)

    def get_subset_frame(self, frame_start, frame_end, shift_to=None):
        """
        Returns emitters that are in the frame range as specified.

        Args:
            frame_start: (int) lower frame index limit
            frame_end: (int) upper frame index limit (including)
            shift_to:

        Returns:

        """

        ix = (self.frame_ix >= frame_start) * (self.frame_ix <= frame_end)
        em = self[ix]
        if not shift_to:
            return em
        else:
            if em.num_emitter != 0:  # shifting makes only sense if we have an emitter.
                raise ValueError
            return em

    @property
    def single_frame(self):
        """
        Check if all emitters belong to the same frame.

        Returns:
            (bool)
        """
        return True if torch.unique(self.frame_ix).shape[0] == 1 else False

    def split_in_frames(self, ix_low: int = 0, ix_up: int = None):
        """
        Splits a set of emitters in a list of emittersets based on their respective frame index.

        Args:
            ix_low: (int, 0) lower bound
            ix_up: (int, None) upper bound

        Returns:

        """

        """The first frame is assumed to be 0. If it's negative go to the lowest negative."""
        ix_low = ix_low if ix_low is not None else self.frame_ix.min().item()
        ix_up = ix_up if ix_up is not None else self.frame_ix.max().item()

        return gutil.split_sliceable(x=self, x_ix=self.frame_ix, ix_low=ix_low, ix_high=ix_up)

    def _convert_coordinates(self, factor=None, shift=None, axis=None):
        """
        Convert coordinates. Order: factor -> shift -> axis

        Args:
            factor: (torch.Tensor, None)
            shift: (torch.Tensor, None)
            axis: (list)

        Returns:
            xyz (torch.Tensor) modified coordinates.

        """

        xyz = self.xyz.clone()

        if factor is not None:
            if factor.size(0) == 2:
                factor = torch.cat((factor, torch.tensor([1.])), 0)

            xyz = xyz * factor.float().unsqueeze(0)
        if shift is not None:
            xyz += shift.float().unsqueeze(0)
        if axis is not None:
            xyz = xyz[:, axis]

        return xyz

    def convert_em(self, factor=None, shift=None, axis=None, frame_shift=None, new_xy_unit=None):
        """
        Returns a modified copy of this set of emitters.

        Args:
            factor: (torch.Tensor, None)
            shift: (torch.Tensor, None)
            axis: (list)
            frame_shift:
            new_xy_unit:

        Returns:
            EmitterSet: converted emitterset
        """

        emn = self.clone()

        emn.xyz = emn._convert_coordinates(factor, shift, axis)

        if frame_shift is not None:
            emn.frame_ix += frame_shift

        if new_xy_unit is not None:
            emn.xy_unit = new_xy_unit

        return emn

    def convert_em_(self, factor=None, shift=None, axis=None, frame_shift=0, new_xy_unit=None):
        """
        Inplace conversion of emiterset.
        The order of coordinate conversion is factor -> shift -> axis.
        Factor multiplies xyz by a factor. Shift shifts the coordinates. Axis permutes the axis.

        Args:
            factor: (torch.Tensor, None)
            shift: (torch.Tensor, None)
            axis: (list)
            frame_shift:
            new_xy_unit:

        Returns:

        """
        self.xyz = self._convert_coordinates(factor, shift, axis)
        self.frame_ix += frame_shift
        if new_xy_unit is not None:
            self.xy_unit = new_xy_unit

    def populate_crlb(self, psf, **kwargs):
        raise NotImplementedError

    def write_to_csv(self, filename, xy_unit=None, comments=None, plain_header=False, xy_unit2=None):
        """
        Writes the emitterset to a csv file.

        Args:
            filename:  csv file name
            xy_unit:  xy unit (typically 'nm' or 'px') for automatic conversion
            comments:  additional comments to put into the csv
            plain_header: no # at beginning of first line

        Returns:
            grand_matrix: (torch.Tensor) the matrix which was effectively written to csv

        """

        grand_matrix = self.compute_grand_matrix(xy_unit=xy_unit, xy_unit2=xy_unit2)

        # reorder the grand_matrix according to the header below
        grand_matrix = grand_matrix[:, [5, 4, 0, 1, 2, 3, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]]

        header = 'id, frame_ix, x, y, z, phot, prob, bg, x_cr, y_cr, z_cr, phot_cr, bg_cr, x2, y2, z2' \
                 '\nThis is an export from ' \
                 'DeepSMLM.\n' \
                 'Total number of emitters: {}'.format(len(self))

        if comments is not None:
            header += '\nComment during export: {}'.format(comments)
        np.savetxt(filename, grand_matrix.numpy(), delimiter=',', header=header)

        if plain_header:
            with open(filename, "r+") as f:
                content = f.read()  # read everything in the file
                content = content[2:]  # remove hashtag at first line (matlab ...)

            with open(filename, "w") as f:
                f.write(content)  # write the file again

        return grand_matrix

    def write_to_csv_format(self, filename, xy_unit=None, xy_unit2=None, comments=None,
                            xyz_shift=None, frame_shift=None, axis=None, plain_header=False, lud=None, lud_name=None):
        """
        Transforms the data and writes it to a csv.
        Args:
            filename:
            xy_unit:
            xy_unit2: secondary xy unit
            comments:
            xyz_shift:
            frame_shift:
            axis:
            plain_header: (bool) remove hashtag in first line of csv
            lud: look-up-dictionary, replaces the need for all keyword-arguments and uses a predefined dictionary
            lud_name: name of a look-up-dictionary predifined in the code base.

        Returns:
            (None)
        """
        import deepsmlm.generic.inout.csv_in_out as tra
        """Checks before actual run"""
        # lud and lud_name are XOR
        if lud is not None and lud_name is not None:
            raise ValueError("You can not specify lud and lud_name at the same time.")

        if (lud is not None or lud_name is not None) and (xyz_shift is not None or axis is not None):
            raise ValueError("You can not specify factor, shift, axis and lud / lud_name at the same time.")

        if lud_name is not None:
            lud = tra.pre_trafo[lud_name]
        if lud_name is not None or lud is not None:
            xyz_shift = torch.tensor(lud['xyz_shift'])
            xy_unit = lud['xy_unit']
            xy_unit2 = lud['xy_unit2']
            frame_shift = lud['frame_shift']
            axis = lud['axis']
            plain_header = lud['plain_header']
            comments = lud['comments']

        em_clone = self.convert_em(factor=None,
                                   shift=xyz_shift,
                                   axis=axis,
                                   frame_shift=frame_shift,
                                   new_xy_unit=None)

        em_clone.write_to_csv(filename, xy_unit, comments, plain_header=plain_header, xy_unit2=xy_unit2)

    @staticmethod
    def read_csv(filename):
        warnings.warn("This is not the proper way to save and store emittersets.")
        grand_matrix = np.loadtxt(filename, delimiter=",", comments='#')
        grand_matrix = torch.from_numpy(grand_matrix).float()
        if grand_matrix.size(1) == 7:
            return EmitterSet(xyz=grand_matrix[:, 2:5], frame_ix=grand_matrix[:, 1],
                              phot=grand_matrix[:, 5], id=grand_matrix[:, 0],
                              prob=grand_matrix[:, 6])
        else:
            return EmitterSet(xyz=grand_matrix[:, 2:5], frame_ix=grand_matrix[:, 1],
                              phot=grand_matrix[:, 5], id=grand_matrix[:, 0])


class RandomEmitterSet(EmitterSet):
    """
    A helper calss when we only want to provide a number of emitters.
    """

    def __init__(self, num_emitters, extent=32, xy_unit='px'):
        """

        :param num_emitters:
        """
        xyz = torch.rand((num_emitters, 3)) * extent
        super().__init__(xyz, torch.ones_like(xyz[:, 0]), torch.zeros_like(xyz[:, 0]).int(), xy_unit=xy_unit)

    def _inplace_replace(self, em):
        super().__init__(xyz=em.xyz,
                         phot=em.phot,
                         frame_ix=em.frame_ix,
                         id=em.id,
                         prob=em.prob,
                         bg=em.bg,
                         xyz_cr=em.xyz_cr,
                         phot_cr=em.phot_cr,
                         bg_cr=em.bg_cr,
                         sanity_check=False,
                         xy_unit=em.xy_unit,
                         px_size=em.px_size)


class CoordinateOnlyEmitter(EmitterSet):
    """
    A helper class when we only want to provide xyz, but not photons and frame_ix.
    Useful for testing. Photons will be tensor of 1, frame_ix tensor of 0.
    """

    def __init__(self, xyz, xy_unit=None):
        """

        :param xyz: (torch.tensor) N x 2, N x 3
        """
        super().__init__(xyz, torch.ones_like(xyz[:, 0]), torch.zeros_like(xyz[:, 0]).int(), xy_unit=xy_unit)

    def _inplace_replace(self, em):
        super().__init__(xyz=em.xyz,
                         phot=em.phot,
                         frame_ix=em.frame_ix,
                         id=em.id,
                         prob=em.prob,
                         bg=em.bg,
                         xyz_cr=em.xyz_cr,
                         phot_cr=em.phot_cr,
                         bg_cr=em.bg_cr,
                         sanity_check=False,
                         xy_unit=em.xy_unit,
                         px_size=em.px_size)


class EmptyEmitterSet(CoordinateOnlyEmitter):
    """An empty emitter set."""

    def __init__(self):
        super().__init__(torch.zeros((0, 3)))

    def _inplace_replace(self, em):
        super().__init__(xyz=em.xyz,
                         phot=em.phot,
                         frame_ix=em.frame_ix,
                         id=em.id,
                         prob=em.prob,
                         bg=em.bg,
                         xyz_cr=em.xyz_cr,
                         phot_cr=em.phot_cr,
                         bg_cr=em.bg_cr,
                         sanity_check=False,
                         xy_unit=em.xy_unit,
                         px_size=em.px_size)


class LooseEmitterSet:
    """
    Related to the standard EmitterSet. However, here we do not specify a frame_ix but rather a (non-integer)
    initial point in time where the emitter starts to blink and an on-time.

    Attributes:
        xyz (torch.Tensor): coordinates. Dimension: N x 3
        intensity (torch.Tensor): intensity, i.e. photon flux per time unit. Dimension N
        id (torch.Tensor, int): identity of the emitter. Dimension: N
        t0 (torch.Tensor, float): initial blink event. Dimension: N
        ontime (torch.Tensor): duration in frame-time units how long the emitter blinks. Dimension N
        xy_unit (string): unit of the coordinates
    """

    def __init__(self, xyz: torch.Tensor, intensity: torch.Tensor, ontime: torch.Tensor, t0: torch.Tensor,
                 id: torch.Tensor = None, xy_unit=None):
        """

        Args:
            xyz (torch.Tensor): coordinates. Dimension: N x 3
            intensity (torch.Tensor): intensity, i.e. photon flux per time unit. Dimension N
            t0 (torch.Tensor, float): initial blink event. Dimension: N
            ontime (torch.Tensor): duration in frame-time units how long the emitter blinks. Dimension N
            id (torch.Tensor, int, optional): identity of the emitter. Dimension: N
            xy_unit (string): unit of the coordinates
        """

        """If no ID specified, give them one."""
        if id is None:
            id = torch.arange(xyz.shape[0])

        self.xyz = xyz
        self.xy_unit = xy_unit
        self._phot = None
        self.intensity = intensity
        self.id = id
        self.t0 = t0
        self.ontime = ontime

    @property
    def te(self):  # end time
        return self.t0 + self.ontime

    def _distribute_framewise(self):
        """
        Distributes the emitters framewise and prepares them for EmitterSet format.

        Returns:
            xyz_ (torch.Tensor): coordinates
            phot_ (torch.Tensor): photon count
            frame_ (torch.Tensor): frame indices (the actual distribution)
            id_ (torch.Tensor): identities

        """
        frame_start = torch.floor(self.t0)
        frame_last = torch.ceil(self.te)
        frame_dur = (frame_last - frame_start).type(torch.LongTensor)

        num_emitter_brut = frame_dur.sum()

        xyz_ = torch.zeros(num_emitter_brut, self.xyz.shape[1])
        phot_ = torch.zeros_like(xyz_[:, 0])
        frame_ix_ = torch.zeros_like(phot_)
        id_ = torch.zeros_like(frame_ix_)

        c = 0
        for i in range(self.xyz.shape[0]):  # loop over emitters
            for j in range(frame_dur[i]):  # loop over its frames
                xyz_[c, :] = self.xyz[i]
                frame_ix_[c] = frame_start[i] + j
                id_[c] = self.id[i]

                """Calculate time on frame and multiply that by the intensity."""
                ontime_on_frame = torch.min(self.te[i], frame_ix_[c] + 1) - torch.max(self.t0[i], frame_ix_[c])
                phot_[c] = ontime_on_frame * self.intensity[i]  # photon flux times on-time = photons

                c += 1

        return xyz_, phot_, frame_ix_, id_

    def return_emitterset(self):
        """
        Returns EmitterSet with distributed emitters.

        Returns:
            EmitterSet
        """

        xyz_, phot_, frame_ix_, id_ = self._distribute_framewise()
        return EmitterSet(xyz_, phot_, frame_ix_.int(), id_.int(), xy_unit=self.xy_unit)


