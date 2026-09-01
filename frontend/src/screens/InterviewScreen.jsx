import { useState } from "react";
import React from "react";
import Layout from "../components/Layout";
import Avatar from "../components/Avatar";


const INTERVIEWER = "interviewer";

export default function InterviewScreen() {
    return (
        <Layout>
            <div style={style.painel}>
                <Avatar size={200} />
                <div style={style.pergunta}>
<span style={{fontFamily: "DM Sans", fontWeight: "bold", fontSize: 12, color: "#7fa89f"}}>PERGUNTA DO INTERVIEWER: </span>
                </div>
            </div>

        </Layout>
    );
}



const style = {
    painel: {
        alignItems: "center",
        textAlign: "center",
         flexDirection: "column",
          display: "flex",
          maxWidth: 700, 
           width: "100%"
    },
    pergunta: {
        width: "100%",
        maxWidth: 700,
        marginTop: 40,
        height: "auto",
        minHeight: 140,
        backgroundColor: "#e4f3f0",
        borderRadius: 12,
        boxShadow: "0px 4px 12px rgba(0, 0, 0, 0.1)",
        boxSizing: "border-box",
    }
};