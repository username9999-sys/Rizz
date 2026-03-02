/**
 * Rizz-Project Main Module
 */

function greet() {
    console.log("Hello from Rizz-Project!");
    console.log("Running on Node.js");
}

module.exports = { greet };

// Run if executed directly
if (require.main === module) {
    greet();
}
