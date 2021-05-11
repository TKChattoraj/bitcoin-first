// Copyright (c) 2019-2020 The Bitcoin Core developers
// Distributed under the MIT software license, see the accompanying
// file COPYING or http://www.opensource.org/licenses/mit-license.php.
//
#include <test/util/setup_common.h>
#include <util/system.h>
#include <univalue.h>

#ifdef HAVE_BOOST_PROCESS
#include <boost/process.hpp>
#endif // HAVE_BOOST_PROCESS

#include <boost/test/unit_test.hpp>

BOOST_FIXTURE_TEST_SUITE(system_tests, BasicTestingSetup)

// At least one test is required (in case HAVE_BOOST_PROCESS is not defined).
// Workaround for https://github.com/bitcoin/bitcoin/issues/19128
BOOST_AUTO_TEST_CASE(dummy)
{
    BOOST_CHECK(true);
}

#ifdef HAVE_BOOST_PROCESS

bool checkMessage(const std::runtime_error& ex)
{
    // tkc comment:  checkcase:  you can't even start the process--windows can't find the process exe file
    // On Linux & Mac: "No such file or directory"
    // On Windows: "The system cannot find the file specified."
    const std::string what(ex.what());
    std::cout << "checkMessage:  " <<what << std::endl;
    BOOST_CHECK(what.find("file") != std::string::npos);
    return true;
}

bool checkMessageFalse(const std::runtime_error& ex)
{
    //tkc comment:  checkcase:  you can start the process, but can't run it properly--windows can start the command window but is not give a valid command
    //BOOST_CHECK_EQUAL(ex.what(), std::string("RunCommandParseJSON error: process(false) returned 1: \n"));
    const std::string what(ex.what());
    std::cout << "checkMessageFalse:  " << what << std::endl;
    BOOST_CHECK(what.find("returned 1") != std::string::npos);
    return true;
}

bool checkMessageStdErr(const std::runtime_error& ex)
{
    //tkc comment:  checkcase:  you can start the process, give it a legitimate command, but use bad input
    //tkc comment:  windows can start the command window, recieve a legitimate command, but bad input data to that command
    const std::string what(ex.what());
    std::cout << "checkMessageStdErr:  " << what << std::endl;
    BOOST_CHECK(what.find("RunCommandParseJSON error:") != std::string::npos);
    return checkMessage(ex);
}

BOOST_AUTO_TEST_CASE(run_command)
{
    {
        const UniValue result = RunCommandParseJSON("");
        BOOST_CHECK(result.isNull());
    }
    {
#ifdef WIN32
        // Windows requires single quotes to prevent escaping double quotes from the JSON...
        const UniValue result = RunCommandParseJSON("cmd.exe /c echo '{\"success\": true}'");
        //const UniValue result = RunCommandParseJSON("echo '{\"success\": true}'");
        //const UniValue result = RunCommandParseJSON("cmd.exe", "/c echo '{\"success\": \"true\"}'");
#else
        // ... but Linux and macOS echo a single quote if it's used
        const UniValue result = RunCommandParseJSON("echo \"{\"success\": true}\"");
#endif
        BOOST_CHECK(result.isObject());
        const UniValue& success = find_value(result, "success");
        BOOST_CHECK(!success.isNull());
        BOOST_CHECK_EQUAL(success.getBool(), true);
    }
    {
        // An invalid command is handled by Boost
       
        // tkc comment:  Not able to even start the command window process
        std::cout << "invalid_command" << std::endl;
        BOOST_CHECK_EXCEPTION(RunCommandParseJSON("invalid_command"), boost::process::process_error, checkMessage); // Command failed
        std::cout << "*************completed invalid_command*************" << std::endl;
        //BOOST_CHECK_EXCEPTION(RunCommandParseJSON("cmd.exe /c invalid_command"), boost::process::process_error, checkMessage); // Command failed
    }
    {
        // Return non-zero exit code, no output to stderr
       
        //BOOST_CHECK_EXCEPTION(RunCommandParseJSON("false"), std::runtime_error, checkMessageFalse);

        // tkc comment:  Able to start the command window process but told to execute an invalide command
        std::cout << "false" << std::endl;
        BOOST_CHECK_EXCEPTION(RunCommandParseJSON("cmd.exe /c false"), std::runtime_error, checkMessageFalse);
        std::cout << "*************completed false*************" << std::endl;
    }
    {
        // tkc comment:  Able to start the command window process, receive a legitimate command but invalid data input to that command
        // Return non-zero exit code, with error message for stderr
        //BOOST_CHECK_EXCEPTION(RunCommandParseJSON("ls nosuchfile"), std::runtime_error, checkMessageStdErr);
        std::cout << "dir nonsuchfile" << std::endl;
        BOOST_CHECK_EXCEPTION(RunCommandParseJSON("cmd.exe /c dir nosuchfile"), std::runtime_error, checkMessageStdErr);
        std::cout << "*************completed dir nonsuchfile*************" << std::endl;
    }
    {
        // tkc comment:  Able to start command window, execute legitimate command, but the resulting output is invalid JSON
        //BOOST_REQUIRE_THROW(RunCommandParseJSON("echo \"{\""), std::runtime_error); // Unable to parse JSON
        std::cout << "echo '{'" << std::endl;
        BOOST_REQUIRE_THROW(RunCommandParseJSON("cmd.exe /c echo '{'"), std::runtime_error); // Unable to parse JSON
        std::cout << "*************completed echo '{'*************" << std::endl;
    }
    // Test std::in, except for Windows
#ifndef WIN32
    {
        const UniValue result = RunCommandParseJSON("cat", "{\"success\": true}");
        BOOST_CHECK(result.isObject());
        const UniValue& success = find_value(result, "success");
        BOOST_CHECK(!success.isNull());
        BOOST_CHECK_EQUAL(success.getBool(), true);
    }
#endif
}
#endif // HAVE_BOOST_PROCESS

BOOST_AUTO_TEST_SUITE_END()
