# Build of the native backend for Python wheels (scikit-build-core).
# The Makefile does the same for local development.  Both must compile
# with exactly the same numerical flags (a test compares them).
cmake_minimum_required(VERSION 3.21)
project(elliprof LANGUAGES Fortran)

if(NOT CMAKE_Fortran_COMPILER_ID STREQUAL "GNU")
  message(FATAL_ERROR "elliprof needs GNU Fortran (gfortran); found "
                      "${CMAKE_Fortran_COMPILER_ID}")
endif()

# ---- numerical flags --------------------------------------------------
# Identical to FFLAGS in the Makefile.  Never add bounds checking,
# -O2/-O3, -ffast-math or -march: see the Makefile.  CMake's own
# per-build-type flags (Release adds -O3) are cleared so that nothing
# else reaches the compiler.
set(ELLIPROF_FFLAGS -O -g -fno-automatic -ffp-contract=off)
foreach(cfg "" _RELEASE _DEBUG _RELWITHDEBINFO _MINSIZEREL)
  set(CMAKE_Fortran_FLAGS${cfg} "" CACHE STRING "" FORCE)
endforeach()

# ---- version ----------------------------------------------------------
file(READ "${PROJECT_SOURCE_DIR}/VERSION" ELLIPROF_VERSION)
string(STRIP "${ELLIPROF_VERSION}" ELLIPROF_VERSION)
file(WRITE "${PROJECT_BINARY_DIR}/version.inc"
  "      CHARACTER*(*) VERSTR\n"
  "      PARAMETER (VERSTR='${ELLIPROF_VERSION}')\n")

# ---- CFITSIO ----------------------------------------------------------
# Release wheels link a static CFITSIO built from source (CFITSIO_DIR);
# otherwise any installed CFITSIO is used.
option(ELLIPROF_STATIC_CFITSIO "Prefer libcfitsio.a" OFF)
set(_cfitsio_hints "$ENV{CFITSIO_DIR}" "${CFITSIO_DIR}")
if(ELLIPROF_STATIC_CFITSIO)
  # release wheels: the static library from CFITSIO_DIR, or nothing
  find_library(CFITSIO_LIBRARY NAMES libcfitsio.a
               HINTS ${_cfitsio_hints} PATH_SUFFIXES lib lib64
               NO_DEFAULT_PATH)
  if(NOT CFITSIO_LIBRARY)
    message(FATAL_ERROR "ELLIPROF_STATIC_CFITSIO=ON but no libcfitsio.a in "
      "CFITSIO_DIR='$ENV{CFITSIO_DIR}' (run tools/ci/build_cfitsio.sh)")
  endif()
else()
  find_library(CFITSIO_LIBRARY NAMES cfitsio
               HINTS ${_cfitsio_hints} PATH_SUFFIXES lib lib64)
endif()
if(NOT CFITSIO_LIBRARY)
  find_package(PkgConfig QUIET)
  if(PkgConfig_FOUND)
    pkg_check_modules(CFITSIO QUIET cfitsio)
    if(CFITSIO_FOUND)
      find_library(CFITSIO_LIBRARY NAMES cfitsio
                   HINTS ${CFITSIO_LIBRARY_DIRS})
    endif()
  endif()
endif()
if(NOT CFITSIO_LIBRARY)
  message(FATAL_ERROR "CFITSIO not found.  Install it (brew install "
    "cfitsio / apt install libcfitsio-dev / MSYS2 mingw-w64-ucrt-x86_64-"
    "cfitsio) or set CFITSIO_DIR.")
endif()
message(STATUS "CFITSIO: ${CFITSIO_LIBRARY}")
set(_extra_libs "")
if(CFITSIO_LIBRARY MATCHES "\\.a$")
  # a static CFITSIO needs zlib (and nothing else in our source build)
  find_package(ZLIB REQUIRED)
  list(APPEND _extra_libs ZLIB::ZLIB)
  if(NOT WIN32 AND NOT APPLE)
    list(APPEND _extra_libs m)
  endif()
endif()

# ---- the backend ------------------------------------------------------
set(ORIGINAL elliprof jtutil gcfit assign dissect value operate variable
             upper)
set(SHIM main stubs fitsio profout maskio prep)
set(SOURCES "")
foreach(f ${ORIGINAL})
  list(APPEND SOURCES "src/original/${f}.f")
endforeach()
foreach(f ${SHIM})
  list(APPEND SOURCES "src/shim/${f}.f")
endforeach()

# The legacy fixed-form sources must reach the compiler exactly as in the
# Makefile build: no C preprocessor (CMake's Ninja generator would
# otherwise run them through `gfortran -cpp -E` first).
set_source_files_properties(${SOURCES} PROPERTIES Fortran_PREPROCESS OFF)

add_executable(elliprof_native ${SOURCES})
target_include_directories(elliprof_native PRIVATE
  "${PROJECT_SOURCE_DIR}/include" "${PROJECT_BINARY_DIR}")
target_compile_options(elliprof_native PRIVATE ${ELLIPROF_FFLAGS})
target_link_libraries(elliprof_native PRIVATE ${CFITSIO_LIBRARY}
                      ${_extra_libs})
# scikit-build-core installs relative paths into the wheel's package dir
install(TARGETS elliprof_native RUNTIME DESTINATION elliprof/_bin)

# Windows (MinGW): the backend runs as a separate process, which never
# sees the DLL directory delvewheel registers for the Python process.
# Its gfortran runtime and zlib DLLs go next to it instead, where Windows
# always looks first.
if(MINGW)
  get_filename_component(_mingw_bin "${CMAKE_Fortran_COMPILER}" DIRECTORY)
  install(CODE "
    file(GET_RUNTIME_DEPENDENCIES
      EXECUTABLES \"$<TARGET_FILE:elliprof_native>\"
      DIRECTORIES \"${_mingw_bin}\"
      RESOLVED_DEPENDENCIES_VAR _deps
      UNRESOLVED_DEPENDENCIES_VAR _unresolved
      PRE_EXCLUDE_REGEXES \"^[Aa][Pp][Ii]-[Mm][Ss]-\" \"^[Ee][Xx][Tt]-[Mm][Ss]-\"
      POST_EXCLUDE_REGEXES \"[Ss][Yy][Ss][Tt][Ee][Mm]32\")
    foreach(_d \${_deps})
      message(STATUS \"bundling \${_d}\")
    endforeach()
    file(INSTALL \${_deps}
         DESTINATION \"\${CMAKE_INSTALL_PREFIX}/elliprof/_bin\")
  ")
endif()

# Notices travel with every wheel
install(FILES LICENSE THIRD_PARTY_NOTICES.md
        DESTINATION elliprof/_notices)
# licence texts of the runtime libraries bundled in the wheels
file(GLOB _runtime_licenses "${PROJECT_SOURCE_DIR}/licenses/*.txt")
install(FILES ${_runtime_licenses} DESTINATION elliprof/_notices)
if(CFITSIO_LIBRARY MATCHES "\\.a$")
  get_filename_component(_cfitsio_prefix "${CFITSIO_LIBRARY}" DIRECTORY)
  get_filename_component(_cfitsio_prefix "${_cfitsio_prefix}" DIRECTORY)
  set(_cfitsio_license "${_cfitsio_prefix}/share/licenses/cfitsio/License.txt")
  if(EXISTS "${_cfitsio_license}")
    install(FILES "${_cfitsio_license}" DESTINATION elliprof/_notices
            RENAME CFITSIO_License.txt)
  endif()
endif()
