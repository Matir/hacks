package arch

import "strings"

type ArchInfo struct {
	Name         string
	KSArch       int
	KSMode       int
	CSArch       int
	CSMode       int
}

var SupportedArches = map[string]ArchInfo{
	"x86_64": {
		Name:   "x86_64",
		KSArch: 1, // KS_ARCH_X86
		KSMode: 8, // KS_MODE_64
		CSArch: 3, // CS_ARCH_X86
		CSMode: 4, // CS_MODE_64
	},
	"x86": {
		Name:   "x86",
		KSArch: 1, // KS_ARCH_X86
		KSMode: 4, // KS_MODE_32
		CSArch: 3, // CS_ARCH_X86
		CSMode: 2, // CS_MODE_32
	},
	"x86_16": {
		Name:   "x86_16",
		KSArch: 1, // KS_ARCH_X86
		KSMode: 2, // KS_MODE_16
		CSArch: 3, // CS_ARCH_X86
		CSMode: 2, // CS_MODE_16
	},
	"arm": {
		Name:   "arm",
		KSArch: 2, // KS_ARCH_ARM
		KSMode: 1, // KS_MODE_ARM
		CSArch: 0, // CS_ARCH_ARM
		CSMode: 0, // CS_MODE_ARM
	},
	"thumb": {
		Name:   "thumb",
		KSArch: 2,  // KS_ARCH_ARM
		KSMode: 16, // KS_MODE_THUMB
		CSArch: 0,  // CS_ARCH_ARM
		CSMode: 16, // CS_MODE_THUMB
	},
	"arm64": {
		Name:   "arm64",
		KSArch: 3, // KS_ARCH_ARM64
		KSMode: 0, // KS_MODE_LITTLE_ENDIAN
		CSArch: 1, // CS_ARCH_ARM64
		CSMode: 0, // CS_MODE_LITTLE_ENDIAN
	},
	"mips": {
		Name:   "mips",
		KSArch: 4, // KS_ARCH_MIPS
		KSMode: 0, // KS_MODE_MIPS32 + KS_MODE_LITTLE_ENDIAN
		CSArch: 2, // CS_ARCH_MIPS
		CSMode: 0, // CS_MODE_MIPS32 + CS_MODE_LITTLE_ENDIAN
	},
	"mips64": {
		Name:   "mips64",
		KSArch: 4, // KS_ARCH_MIPS
		KSMode: 8, // KS_MODE_MIPS64
		CSArch: 2, // CS_ARCH_MIPS
		CSMode: 8, // CS_MODE_MIPS64
	},
	"ppc": {
		Name:   "ppc",
		KSArch: 5, // KS_ARCH_PPC
		KSMode: 4, // KS_MODE_PPC32
		CSArch: 4, // CS_ARCH_PPC
		CSMode: 4, // CS_MODE_32
	},
	"ppc64": {
		Name:   "ppc64",
		KSArch: 5, // KS_ARCH_PPC
		KSMode: 8, // KS_MODE_PPC64
		CSArch: 4, // CS_ARCH_PPC
		CSMode: 8, // CS_MODE_64
	},
}

func GetArch(name string) (ArchInfo, bool) {
	info, ok := SupportedArches[strings.ToLower(name)]
	return info, ok
}
