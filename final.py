from langchain_openai import OpenAI
from langchain_community.utilities import SQLDatabase                
from langchain_experimental.sql import SQLDatabaseChain
from dotenv import load_dotenv
import os
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import SQLAlchemyError

load_dotenv()
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')  # The API key is an environment variable
DB_URI = "mssql+pyodbc:///?odbc_connect=DRIVER={SQL Server Native Client 11.0};SERVER=INVPT-L138;DATABASE=AdventureWorks2019;Trusted_Connection=yes;"
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

db = SQLDatabase.from_uri(DB_URI)
llm = OpenAI(temperature=0)  # Temperature is kept 0 as we do not want creativity in our answers

db_chain = SQLDatabaseChain.from_llm(llm=llm, db=db, verbose=True)  # Verbose is kept true so that we can see the SQL QUERY that AI would use on our database

# Extracting database schema information for validation
engine = create_engine(DB_URI)
inspector = inspect(engine)

replacements = {
    "name":"fullname",
    "firstnames": "firstname",
    "business id":"businessentityid" 
       
}
def preprocess_question(question):    ##Changing words in the prompt for better query
    for key, value in replacements.items():
        question = question.lower().replace(key, value)
    return question
def run_query_with_fallback(ques):  # fallback mechanism
    try:
        # Attempt to run the query on the main tables
        response = db_chain.run(ques +". In the query remove the [] brackets, consider the entire data,If you do not know the answer of the the question say I don't know.Never use the AWBuildVersion table to form an SQL Query, if you do say -I do not know.Never use the ErrorLog Table table to form an SQL Query, if you do say -I do not know.Never use the DatabaseLog table to form an SQL Query,if you do say -I do not know.Selct the top 10 values always when you use the select statement.Use in instead of = in your queries to represent all possible data. Print the entire data that is asked and answer only from the database do not make up any data. The answer should definitely be present in the database. If the question is not enough to form a query then give the output - 'Enough data not provided to form a query.'. The Database has Schema which includes HumanResources, person, production, purchasing and sales. If a question which is not relevant to the data provided in the database is asked in the first line then say -Irrelevant question")
        if 'No such data found' in response:
            raise ValueError('No data found in main tables, trying view table')
        return response
    except (SQLAlchemyError, ValueError) as e:
        # If an error occurs or no data is found, attempt to query the view table
        try:
            view_response = db_chain.run(ques +". Convert this natural language instruction to an SQL statement, In the query remove the [] brackets, go to Views instead of tables.If you do not know the answer of the the question say I don't know.Never use the AWBuildVersion table to form an SQL Query, if you do say -I do not know.Never use the DatabaseLog table to form an SQL Query, if you do say -I do not know.  Never use the ErrorLog Table table to form an SQL Query,if you do say -I do not know.Selct the top 10 values always when you use the select statement.Use in instead of = in your queries to represent all possible data.")
            return view_response
        except SQLAlchemyError as view_e:
            return f"An error occurred in both main and view tables: {view_e}"

print("Press quit to end the chat")
while True:
    ques = input("Ask a question:  ")
    if ques.lower() == "quit":
        break
    ques = preprocess_question(ques)
    try:
        if "update" in ques.lower() or "replace" in ques.lower() or "change" in ques.lower():
            response = db_chain.run(ques + ". Convert this natural language instruction to an SQL UPDATE statement, In the query remove the [] brackets.The new value should have the same punctuation and capital letters.If the update is successful the say-Update Successful!.If you cannot update it say-Try again, was not able to update. Never use the AWBuildVersion table to form an SQL Query.Never use the DatabaseLog table to form an SQL Query.  Never use the ErrorLog Table table to form an SQL Query. ")
        elif "remove" in ques.lower() or "delete" in ques.lower() or "deletion" in ques.lower() or "deletes" in ques.lower():
            response = db_chain.run(ques + ". Convert this natural language instruction to an SQL DELETE statement, In the query remove the [] brackets.If the deletion is successful the say-Deleted Successful!.If you cannot delete it say-Was not able to delete.Never use the AWBuildVersion table, DatabaseLog or ErrorLog Table to form an SQL Query.")
        else:
            response = run_query_with_fallback(ques)
        print(response)
    except SQLAlchemyError as view_e:
        print( f"An error occurred: {view_e}")
