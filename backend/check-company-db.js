const sqlite3 = require('sqlite3').verbose();
const path = require('path');

const dbPath = path.join(__dirname, 'database/companies/company_3_yugcompany_gmail_com.db');
const db = new sqlite3.Database(dbPath);

console.log('📊 Checking Company Database for yugcompany@gmail.com\n');

// Check projects
db.all('SELECT COUNT(*) as count FROM projects', (err, rows) => {
  if (err) {
    console.error('❌ Error checking projects:', err.message);
  } else {
    console.log(`📁 Total Projects: ${rows[0].count}`);
  }
});

// Check company profile
db.all('SELECT * FROM company_profile', (err, rows) => {
  if (err) {
    console.error('❌ Error checking profile:', err.message);
  } else {
    console.log(`\n🏢 Company Profile:`);
    if (rows.length > 0) {
      console.log(JSON.stringify(rows[0], null, 2));
    } else {
      console.log('   No profile data found');
    }
  }
});

// Check files
db.all('SELECT COUNT(*) as count FROM files', (err, rows) => {
  if (err) {
    console.error('❌ Error checking files:', err.message);
  } else {
    console.log(`\n📄 Total Files: ${rows[0].count}`);
  }
});

// Check recent projects
db.all('SELECT * FROM projects ORDER BY created_at DESC LIMIT 5', (err, rows) => {
  if (err) {
    console.error('❌ Error checking recent projects:', err.message);
  } else {
    console.log(`\n📋 Recent Projects:`);
    if (rows.length > 0) {
      rows.forEach((project, i) => {
        console.log(`   ${i + 1}. ${project.project_name} (${project.status}) - ${project.project_id}`);
      });
    } else {
      console.log('   No projects found');
    }
  }
  
  db.close();
});
