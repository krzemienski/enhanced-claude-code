# Functional Testing Instructions for Claude Code Builder v3.0

## CRITICAL TESTING REQUIREMENTS

When you reach the testing phase, you MUST:

1. **EXPECT LONG EXECUTION TIMES**
   - The functional test will run for 10-30 minutes
   - This is NORMAL and EXPECTED
   - You must CONTINUOUSLY monitor the streaming logs
   - DO NOT assume failure just because it takes time

2. **MONITOR STREAMING OUTPUT**
   - Use `tail -f` on log files
   - Watch for progress indicators
   - Track file creation in real-time
   - Monitor cost accumulation
   - Check for error patterns

3. **FUNCTIONAL TEST STAGES**

   Stage 1: Installation Verification
   ```bash
   # Install the package
   cd claude-code-builder
   pip install -e .
   
   # Verify installation
   which claude-code-builder
   claude-code-builder --version
   ```

   Stage 2: CLI Testing
   ```bash
   # Test all CLI commands
   claude-code-builder --help
   claude-code-builder --list-examples
   claude-code-builder --show-costs
   ```

   Stage 3: Full Functional Test
   ```bash
   # Create test output directory
   mkdir -p test-output
   
   # Start the build (THIS WILL TAKE 10-30 MINUTES)
   claude-code-builder examples/simple-api.md \
     --output-dir ./test-output \
     --enable-research \
     --verbose \
     2>&1 | tee test-execution.log &
   
   # Get the process ID
   BUILD_PID=$!
   
   # Monitor in real-time (MUST DO THIS)
   tail -f test-execution.log
   ```

   Stage 4: Progress Monitoring
   ```bash
   # In another terminal or after starting tail -f
   while kill -0 $BUILD_PID 2>/dev/null; do
     echo "Build still running... checking progress"
     
     # Check created files
     find test-output -type f -name "*.py" | wc -l
     
     # Check log for phases
     grep -c "PHASE.*COMPLETE" test-execution.log || echo "0 phases complete"
     
     # Check for errors
     grep -c "ERROR" test-execution.log || echo "0 errors"
     
     # Wait 30 seconds before next check
     sleep 30
   done
   ```

   Stage 5: Validation
   ```bash
   # After completion, validate output
   cd test-output
   
   # Check structure
   find . -name "*.py" | head -20
   
   # Verify key files exist
   test -f setup.py && echo "✓ setup.py exists"
   test -f requirements.txt && echo "✓ requirements.txt exists"
   test -d tests && echo "✓ tests directory exists"
   
   # Try to run the created project's tests
   if [ -f setup.py ]; then
     pip install -e .
     pytest tests/ || echo "Tests not yet implemented"
   fi
   ```

4. **WHAT TO LOOK FOR IN LOGS**

   Good Signs:
   ```
   [PHASE COMPLETE] ✅
   Created: [filename]
   Tool: Write Creating [file]
   Session cost: $X.XX
   Phase X: Y turns, $Z.ZZ
   ```

   Warning Signs (but continue monitoring):
   ```
   Retrying...
   Rate limit encountered
   Waiting...
   ```

   Error Signs (may need intervention):
   ```
   FAILED after 3 attempts
   Critical error:
   Traceback (most recent call last):
   ```

5. **EXPECTED TIMELINE**

   - Phase 0 (AI Planning): 2-5 minutes
   - Phases 1-5: 1-3 minutes each
   - Phases 6-10: 2-5 minutes each
   - Phases 11-15: 3-7 minutes each
   - Testing Phase: 5-10 minutes
   - Total: 25-45 minutes

6. **MEMORY FOR NEXT TIME**

   Remember these key points for future testing:
   - Functional tests ALWAYS take 10-30 minutes
   - You MUST monitor logs continuously
   - File creation happens gradually
   - Costs accumulate over time
   - Some phases take longer than others
   - This is NORMAL BEHAVIOR

DO NOT conclude the test failed just because it's taking time. The build process is SUPPOSED to take this long.
