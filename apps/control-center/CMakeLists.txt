cmake_minimum_required(VERSION 3.21)
project(hscl-control-center VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)

find_package(Qt6 6.5 REQUIRED COMPONENTS Core Gui Qml Quick QuickControls2 LinguistTools Test)

add_library(hscl_backend STATIC src/CliBackend.cpp src/CliBackend.h)
target_link_libraries(hscl_backend PUBLIC Qt6::Core Qt6::Qml)
target_include_directories(hscl_backend PUBLIC src)

add_executable(hscl-control-center src/main.cpp)
target_link_libraries(hscl-control-center PRIVATE hscl_backend Qt6::Gui Qt6::Quick Qt6::QuickControls2)

qt_add_lrelease(hscl-control-center
    TS_FILES i18n/hscl-cc_de.ts i18n/hscl-cc_fr.ts
    QM_FILES_OUTPUT_VARIABLE qm_files)

install(TARGETS hscl-control-center RUNTIME DESTINATION usr/bin)
install(DIRECTORY qml/ DESTINATION usr/share/hscl/control-center/qml)
install(FILES ${qm_files} DESTINATION usr/share/hscl/control-center/i18n)

enable_testing()
add_executable(tst_backend tests/cpp/tst_backend.cpp)
target_link_libraries(tst_backend PRIVATE hscl_backend Qt6::Test)
add_test(NAME backend COMMAND tst_backend)

find_program(QMLTESTRUNNER NAMES qmltestrunner6 qmltestrunner PATHS /usr/lib/qt6/bin)
if(QMLTESTRUNNER)
    add_test(NAME qml COMMAND ${QMLTESTRUNNER} -input ${CMAKE_CURRENT_SOURCE_DIR}/tests/qml)
    set_tests_properties(qml PROPERTIES ENVIRONMENT "QT_QPA_PLATFORM=offscreen")
endif()
