# Tests for submodule.nim
# Run with: nimble test

import unittest
import os

import pocketsocketpkg/submodule

suite "submodule tests":
  
  test "getWelcomeMessage returns 'Hello, World!' when no banner.txt exists":
    let msg = getWelcomeMessage()
    check msg == "Hello, World!"
  
  test "getWelcomeMessage returns banner.txt content when file exists":
    # Create a temporary banner.txt
    let testContent = "Test Banner Content"
    writeFile("banner.txt", testContent)
    
    # Note: getWelcomeMessage checks loaded_template_str first,
    # so we need to test in a fresh state or after the cache check
    let msg = getWelcomeMessage()
    
    # Clean up
    removeFile("banner.txt")
    
    check msg == testContent
  
  # test "getLocalFileContents returns file content when file exists":
  #   # Create a test file
  #   let testFile = "test_file.txt"
  #   let testContent = "Test File Content"
  #   writeFile(testFile, testContent)
    
  #   let content = getLocalFileContents(testFile)
    
  #   # Clean up
  #   removeFile(testFile)
    
  #   check content == testContent
  
  # test "getLocalFileContents returns default template when file missing":
  #   let content = getLocalFileContents("nonexistent_file.txt")
  #   let expectedDefault = """<body onload="ws=new WebSocket('ws://'+location.host).onmessage=e=>document.body.innerHTML=e.data" style="background:#111;color:#ccc"></body>"""
  #   check content == expectedDefault
  
  # test "setLoadedTemplate caches file content":
  #   # Create a test file
  #   let testFile = "test_template.html"
  #   let testContent = "<html>Cached Template</html>"
  #   writeFile(testFile, testContent)
    
  #   # Set the template
  #   setLoadedTemplate(testFile)
    
  #   # Verify by calling getWelcomeMessage (which checks the cache first)
  #   let msg = getWelcomeMessage()
    
  #   # Clean up
  #   removeFile(testFile)
    
  #   check msg == testContent
  
  # test "getCachedLocalFileContents uses cache when available":
  #   # First load something into cache
  #   let testFile = "cached_test.txt"
  #   let testContent = "Cached Content"
  #   writeFile(testFile, testContent)
  #   setLoadedTemplate(testFile)
    
  #   # Now try to get a different file - should return cached content
  #   let result = getCachedLocalFileContents("some_other_file.txt")
    
  #   # Clean up
  #   removeFile(testFile)
    
  #   check result == testContent
